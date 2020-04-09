# ShowCommits Preprocessor

ShowCommits is a preprocessor that appends the history of Git commits corresponding to the current processed file to its content.

## Installation

```bash
$ pip install foliantcontrib.showcommits
```

## Config

To enable the preprocessor, add `showcommits` to `preprocessors` section in the project config:

```yaml
preprocessors:
    - showcommits
```

The preprocessor has a number of options with the following default values:

~~~yaml
preprocessors:
    - showcommits:
        repo_path: !rel_path ./    # Path object that points to the current Foliant project’s top-level (“root”) directory when the preprocessor initializes
        try_default_path: true
        remote_name: origin
        self-hosted: gitlab
        protocol: https
        position: after_content
        date_format: year_first
        escape_html: true
        template: |
            ## File History

            {{startcommits}}
            Commit: [{{hash}}]({{url}}), author: [{{author}}]({{email}}), date: {{date}}

            {{message}}

            ```diff
            {{diff}}
            ```
            {{endcommits}}
        targets: []
~~~

`repo_path`
:   Path to the locally cloned copy of the Git repository that the current Foliant project’s files belong to.

`try_default_path`
:   Flag that tells the preprocessor to try to use the default `repo_path` if user-specified `repo_path` does not exist.

`remote_name`
:   Identifier of remote repository; in most cases you don’t need to override the default value.

`self-hosted`
:   String that defines the rules of commit’s web URL anchor generation when a self-hosted Git repositories management system with web interface is used. Supported values are: `github` for GitHub, `gitlab` for GitLab, and `bitbucket` for BitBucket. If the repo fetch URL hostname is `github.com`, `gitlab.com`, or `bitbucket.org`, the corresponding rules are applied automatically.

`protocol`
:   Web interface URL prefix of a repos management system. Supported values are `https` and `http`.

`position`
:   String that defines where the history of commits should be placed. Supported values are: `after_content` for concatenating the history with the currently processed Markdown file content, and `defined_by_tag` for replacing the tags `<<commits></commits>` with the history.

`date_format`
:   Output date format. If the default value `year_first` is used, the date “December 11, 2019” will be represented as `2019-12-11`. If the `day_first` value is used, this date will be represented as `11.12.2019`.

`escape_html`
:   Flag that tells the preprocessor to replace HTML control characters with corresponding HTML entities in commit messages and diffs: `&` with `&amp;`, `<` with `&lt;`, `>` with `&gt;`, `"` with `&quot;`.

`template`
:   Template to render the history of commits. If the value is a string that contains one or more newlines (`\n`) or double opening curly braces (`{{`), it is interpreted as a template itself. If the value is a string without newlines and any double opening curly braces, or a `Path` object, it is interpreted as a path to the file that contains a template. Template syntax is described below.

`targets`
:   Allowed targets for the preprocessor. If not specified (by default), the preprocessor applies to all targets.

## Usage

You may override the default template to customize the commits history formatting and rendering. Feel free to use Markdown syntax, HTML, CSS, and JavaScript in your custom templates.

In templates, a number of placeholders is supported.

`{{startcommits}}`
:   Beginning of the list of commits that is rendered within a loop. Before this placeholder, you may use some common stuff like an introducing heading or a stylesheet.

`{{endcommits}}`
:   End of the list of commits. After this placeholder, you also may use some common stuff like a paragraph of text or a script.

The following placeholders affect only between the `{{startcommits}}` and `{{endcommits}}`.

`{{hash}}`
:   First 8 digits of the commit hash, e.g. `deadc0de`.

`{{url}}`
:   Web URL of commit with an anchor that points to the certain file, e.g. `https://github.com/foliant-docs/foliant/commit/67138f7c#diff-478b1f78b2146021bce46fbf833eb636`. If you don’t use a repos management system with web interface, you don’t need this placeholder.

`{{author}}`
:   Author name, e.g. `Artemy Lomov`.

`{{email}}`
:   Author email, e.g. `artemy@lomov.ru`.

`{{date}}`
:   Formatted date, e.g. `2019-12-11`.

`{{message}}`
:   Commit message, e.g. `Bump version to 1.0.1.`.

`{{diff}}`
:   Diff between the currently processed Markdown file at a certain commit and the same file at the previous state.
