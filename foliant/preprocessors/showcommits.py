'''
Preprocessor for Foliant documentation authoring tool.

Shows history of Git commits corresponding to the current processed file.
'''

import re
from pathlib import Path
from subprocess import run, PIPE, STDOUT, CalledProcessError

from foliant.utils import output
from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    defaults = {
        'repo_path': Path('./').resolve(),
        'date_format': 'year_first',
        'foreword': '## File History\n\n',
        'template': '''
Commit: [{{hash}}]({{url}}), author: {{author}}, date: {{date}}

{{message}}

```diff
{{diff}}
```
''',
        'afterword': ''
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('showcommits')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

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

        elif self.options['date_format'] == 'day_first':
            date = re.sub(
                date_pattern,
                r'\g<day>.\g<month>.\g<year>',
                markdown_date
            )

        return date

    def process_showcommits(self, markdown_content: str, markdown_file_path: Path) -> str:
        repo_path = Path(self.options['repo_path']).resolve()

        markdown_file_in_src_dir_path = (
            self.config['src_dir'] / markdown_file_path.relative_to(self.working_dir.resolve())
        ).resolve() 

        source_file_path = repo_path / markdown_file_in_src_dir_path.relative_to(self.project_path.resolve())

        self.logger.debug(
            f'Currently processed file path: {markdown_file_path}, ' +
            f'mapped to src dir: {markdown_file_in_src_dir_path}, ' +
            f'repo path: {repo_path}, ' +
            f'source file path: {source_file_path}'
        )

        if not source_file_path.exists():
            warning_message = f'WARNING: file does not exist: {source_file_path}'

            output(warning_message, self.quiet)

            self.logger.warning(warning_message)

            return markdown_content

        command = f'git log -m --patch --date=iso -- "{source_file_path}"'

        self.logger.debug(f'Running the command to get the file history: {command}')

        source_file_git_history = run(
            command,
            cwd=source_file_path.parent,
            shell=True,
            check=True,
            stdout=PIPE,
            stderr=STDOUT
        )

        if source_file_git_history.stdout:
            self.logger.debug('Processing the command output')

            source_file_git_history_decoded = source_file_git_history.stdout.decode('utf8', errors='ignore')
            source_file_git_history_decoded = source_file_git_history_decoded.replace('\r\n', '\n')

            output_history = self.options['foreword']

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
                output_history += (
                    self.options['template']
                ).replace(
                    '{{hash}}', commit_summary.group('hash')
                ).replace(
                    '{{url}}', 'http://' # TODO: get URL
                ).replace(
                    '{{author}}', commit_summary.group('author')
                ).replace(
                    '{{date}}', self._format_date(commit_summary.group('date'))
                ).replace(
                    '{{message}}', commit_summary.group('message')
                ).replace(
                    '{{diff}}', commit_summary.group('diff')
                )

            output_history += self.options['afterword']

        else:
            self.logger.debug('The command returned nothing')

        return markdown_content + '\n\n' + output_history # TODO: support tags

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            with open(markdown_file_path, encoding='utf8') as markdown_file:
                markdown_content = markdown_file.read()

            processed_markdown_content = self.process_showcommits(
                markdown_content,
                markdown_file_path.resolve()
            )

            if processed_markdown_content:
                with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                    markdown_file.write(processed_markdown_content)

        self.logger.info('Preprocessor applied')
