'''
Preprocessor for Foliant documentation authoring tool.

Shows history of Git commits corresponding to the current processed file.
'''

import re
from pathlib import Path
from hashlib import md5, sha1
from subprocess import run, PIPE, STDOUT, CalledProcessError

from foliant.utils import output
from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    defaults = {
        'repo_path': Path('./').resolve(),
        'try_default_path': True,
        'remote_name': 'origin',
        'self-hosted': 'gitlab',
        'protocol': 'https',
        'position': 'after_content',
        'date_format': 'year_first',
        'escape_html': True,
        'template': '''## File History

{{startcommits}}
Commit: [{{hash}}]({{url}}), author: [{{author}}]({{email}}), date: {{date}}

{{message}}

```diff
{{diff}}
```
{{endcommits}}''',
        'targets': []
    }

    tags = 'commits',

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('showcommits')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

    def _get_template(self) -> str:
        if isinstance(self.options['template'], Path) or (
            isinstance(self.options['template'], str)
            and
            '\n' not in self.options['template']
            and
            '{{' not in self.options['template']
        ):
            template_file_path = Path(self.options['template']).resolve()

            self.logger.debug(f'Getting template from the file: {template_file_path}')

            with open(template_file_path, encoding='utf8') as template_file:
                template = template_file.read()

        else:
            self.logger.debug('Template specified directly in config')

            template = str(self.options['template'])

        if not '{{startcommits}}' in template:
            template = '{{startcommits}}' + template

        if not '{{endcommits}}' in template:
            template += '{{endcommits}}'

        return template

    def _get_repo_web_url(self, repo_path: Path) -> str:
        repo_web_url = self.options['protocol'] + '://'

        command = f'git remote show {self.options["remote_name"]}'

        self.logger.debug(f'Running the command to get repo fetch URL: {command}')

        git_remote_info = run(
            command,
            cwd=repo_path,
            shell=True,
            check=True,
            stdout=PIPE,
            stderr=STDOUT
        )

        self.logger.debug('Processing the command output')

        git_remote_info_decoded = git_remote_info.stdout.decode(
            'utf8', errors='ignore'
        ).replace('\r\n', '\n')

        fetch_url_match = re.search(
            r'^  Fetch URL: (?P<url>.+)$',
            git_remote_info_decoded,
            flags=re.MULTILINE
        )

        if fetch_url_match:
            fetch_url = fetch_url_match.group('url')

            self.logger.debug(f'Fetch URL: {fetch_url}')

            if fetch_url.startswith('git'):
                repo_web_url += re.sub(
                    r'^git\@(?P<host>[^:]+):(?P<repo>.+)\.git$',
                    '\g<host>/\g<repo>',
                    fetch_url
                )

            elif fetch_url.startswith('http'):
                repo_web_url += re.sub(
                    r'^https?:\/\/(?P<host>[^\/]+)\/(?P<repo>.+)\.git$',
                    '\g<host>/\g<repo>',
                    fetch_url
                )

            else:
                self.logger.debug('Fetch URL protocol is not supported')

        else:
            warning_message = f'WARNING: cannot get fetch URL for the repo: {repo_path}'

            output(warning_message, self.quiet)

            self.logger.warning(warning_message)

        self.logger.debug(f'Repo Web URL: {repo_web_url}')

        return repo_web_url

    def _get_file_path_anchor(self, repo_web_url: str, source_file_rel_path: Path) -> str:
        host_match = re.match(r'^https?:\/\/(?P<host>[^\/]+)\/', repo_web_url)

        if host_match:
            host = host_match.group('host')

            if host == 'gitlab.com':
                hosting = 'gitlab'

            elif host == 'github.com':
                hosting = 'github'

            elif host == 'bitbucket.org':
                hosting == 'bitbucket'

            else:
                hosting = self.options['self-hosted']

        self.logger.debug(f'Generating file path anchor for commit URL, style: {hosting}')

        if hosting == 'gitlab':
            anchor = f'#{sha1(str(source_file_rel_path).encode()).hexdigest()}'

        elif hosting == 'github':
            anchor = f'#diff-{md5(str(source_file_rel_path).encode()).hexdigest()}'

        elif hosting == 'bitbucket':
            anchor = f'#chg-{source_file_rel_path}'

        else:
            anchor = ''

        self.logger.debug(f'Anchor: {anchor}')

        return anchor

    def _escape_html(self, content: str) -> str:
        return content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def _format_date(self, date: str) -> str:
        date_pattern = re.compile(
            r'^(?P<year>\d{4})\-(?P<month>\d{2})\-(?P<day>\d{2}) (?P<time>\S+) (?P<timezone>\S+)$'
        )

        if self.options['date_format'] == 'year_first':
            date = re.sub(
                date_pattern,
                r'\g<year>-\g<month>-\g<day>',
                date
            )

            self.logger.debug(f'Formatting date, year first: {date}')

        elif self.options['date_format'] == 'day_first':
            date = re.sub(
                date_pattern,
                r'\g<day>.\g<month>.\g<year>',
                date
            )

            self.logger.debug(f'Formatting date, day first: {date}')

        else:
            self.logger.debug(f'Preserving default date formatting: {date}')

        return date

    def process_showcommits(
        self,
        markdown_content: str,
        template: str,
        markdown_file_path: Path,
        repo_path: Path,
        repo_web_url: str
    ) -> str:
        markdown_file_in_src_dir_path = (
            self.config['src_dir'] / markdown_file_path.relative_to(self.working_dir.resolve())
        ).resolve() 

        source_file_rel_path = markdown_file_in_src_dir_path.relative_to(self.project_path.resolve())
        source_file_abs_path = repo_path / source_file_rel_path

        self.logger.debug(
            f'Currently processed file path: {markdown_file_path}, ' +
            f'mapped to src dir: {markdown_file_in_src_dir_path}, ' +
            f'repo path: {repo_path}, ' +
            f'source file path relative to repo path: {source_file_rel_path}, ' +
            f'source file absolute path: {source_file_abs_path}'
        )

        if not source_file_abs_path.exists():
            warning_message = f'WARNING: file does not exist: {source_file_abs_path}'

            output(warning_message, self.quiet)

            self.logger.warning(warning_message)

            return markdown_content

        command = f'git log -m --follow --patch --date=iso -- "{source_file_abs_path}"'

        self.logger.debug(f'Running the command to get the file history: {command}')

        source_file_git_history = run(
            command,
            cwd=source_file_abs_path.parent,
            shell=True,
            check=True,
            stdout=PIPE,
            stderr=STDOUT
        )

        self.logger.debug('Processing the command output')

        source_file_git_history_decoded = source_file_git_history.stdout.decode(
            'utf8', errors='ignore'
        ).replace('\r\n', '\n')

        file_path_anchor = self._get_file_path_anchor(repo_web_url, source_file_rel_path)
        foreword, commits_and_afterword = template.split('{{startcommits}}', maxsplit=1)
        commits_template, afterword = commits_and_afterword.split('{{endcommits}}', maxsplit=1)
        output_history = foreword

        for commit_summary in re.finditer(
            r'commit (?P<hash>[0-9a-f]{8})[0-9a-f]{32}\n' +
            r'((?!commit [0-9a-f]{40}).*\n|\n)*' +
            r'Author: (?P<author>.+)\n' +
            r'Date: +(?P<date>.+)\n\n' +
            r'(?P<message>((?!commit [0-9a-f]{40}|diff \-\-git .+).*\n|\n)+)' +
            r'(' +
            r'diff \-\-git .+\nindex .+\n\-{3} a\/.+\n\+{3} b\/.+\n' +
            r'(?P<diff>((?!commit [0-9a-f]{40}).+\n)+)' +
            r')',
            source_file_git_history_decoded
        ):
            commit_author_match = re.match(
                r'^(?P<name>.+) \<(?P<email>\S+\@\S+)\>$',
                commit_summary.group('author')
            )

            if commit_author_match:
                commit_author = commit_author_match.group('name')
                commit_author_email = commit_author_match.group('email')

            else:
                commit_author = commit_summary.group('author')
                commit_author_email = ''

            commit_message = re.sub(
                r'^ {4}',
                '',
                commit_summary.group('message'),
                flags=re.MULTILINE
            )

            commit_diff = commit_summary.group('diff')

            if self.options['escape_html']:
                commit_message = self._escape_html(commit_message)
                commit_diff = self._escape_html(commit_diff)

            output_history += (
                commits_template
            ).replace(
                '{{hash}}', commit_summary.group('hash')
            ).replace(
                '{{url}}',
                f'{repo_web_url}/commit/{commit_summary.group("hash")}{file_path_anchor}'
            ).replace(
                '{{author}}', commit_author
            ).replace(
                '{{email}}', commit_author_email
            ).replace(
                '{{date}}', self._format_date(commit_summary.group('date'))
            ).replace(
                '{{message}}', commit_message
            ).replace(
                '{{diff}}', commit_diff
            )

        output_history += afterword

        if self.options['position'] == 'after_content':
            markdown_content += '\n\n' + output_history

        elif self.options['position'] == 'defined_by_tag':
            markdown_content = self.pattern.sub(output_history, markdown_content)

        return markdown_content

    def apply(self):
        self.logger.info('Applying preprocessor')

        self.logger.debug(
            f'Allowed targets: {self.options["targets"]}, ' +
            f'current target: {self.context["target"]}'
        )

        if not self.options['targets'] or self.context['target'] in self.options['targets']:
            template = self._get_template()

            repo_path = Path(self.options['repo_path']).resolve()

            self.logger.debug(f'User-specified repo path: {repo_path}')

            if not repo_path.exists() and self.options['try_default_path']:
                repo_path = self.defaults['repo_path']

                self.logger.debug(f'User-specified path does not exist, trying to use the default one: {repo_path}')

            repo_web_url = self._get_repo_web_url(repo_path)

            for markdown_file_path in self.working_dir.rglob('*.md'):
                with open(markdown_file_path, encoding='utf8') as markdown_file:
                    markdown_content = markdown_file.read()

                processed_markdown_content = self.process_showcommits(
                    markdown_content,
                    template,
                    markdown_file_path.resolve(),
                    repo_path,
                    repo_web_url
                )

                if processed_markdown_content:
                    with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                        markdown_file.write(processed_markdown_content)

        self.logger.info('Preprocessor applied')
