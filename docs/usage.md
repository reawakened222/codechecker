# CodeChecker HOWTO

This is lazy dog HOWTO to using CodeChecker analysis.
It invokes Clang Static Analyzer and Clang-Tidy tools to analyze your code.

## Table of Contents
* [Step 1: Integrate CodeChecker into your build system](#step-1)
* [Step 2: Analyze your code](#step-2)
    * [Cross-Compilation](#cross-compilation)
    * [Incremental Analysis](#incremental-analysis)
    * [Analysis Failures](#analysis-failures)
    * [Avoiding or Suppressing False Positives](#false-positives)
* [Step 3: View analysis results in command line or generate static HTML files](#step-3)
* [Step 4: Store analysis results in a CodeChecker DB and visualize results](#step-4)
* [Step 5: Fine tune Analysis configuration](#step-5)
    * [Ignore modules from your analysis](#ignore-modules)
    * [Enable/Disable Checkers](#enable-disable-checkers)
    * [Configure Checkers](#configure-checkers)
    * [Identify files that failed analysis](#identify-files)
* [Step 6: Integrate CodeChecker into your CI loop](#step-6)
    * [Storing & Updating runs](#storing-runs)
    * [ Alternative 1 (RECOMMENDED): Store the results of each commit in the same run](#storing-results)
        * [Jenkins Script](#storing-results-example)
    * [Alternative 2: Store each analysis in a new run](#storing-new-runs)
        * [Jenkins Script](#storing-new-runs-example)
    * [Gerrit Integration](#gerrit)
    * [Programmer checking new bugs in the code after local edit (and compare it to a central database)](#compare)
    * [Setting up user authentication](#authentication)
* [Updating CodeChecker to new version](#upgrade)
* [Unique Report Identifier](#unique-report-identifier)
* [Listing and Counting Reports](#listing-reports)
    * [How reports are counted?](#how-report-are-counted)
    * [Report Uniqueing](#report-uniqueing)
    * [How diffs between runs are calculated?](#diffs-between-runs)

## Step 1: Integrate CodeChecker into your build system <a name="step-1"></a>
CodeChecker only analyzes what is also built by your build system.

1. Select a module to build (open source tmux in this example).
```sh
cd tmux
./configure
```
2. Clean that module. e.g. `make clean`
```sh
make clean
```
3. Log your build:
```sh
CodeChecker log -b "make" -o compilation.json
```
4. Check the contents of compilation.json. If everything goes well it should
contain the `gcc` calls.
```sh
cat ./compilation.json
```

**What to do if the `compilation.json` is empty?**

* Make sure that your build system actually invoked the compiler (e.g. `gcc`,
`g++`).
  In case your software was built once (and the binaries are already
  generated), the compiler will not be invoked. In this case do a build
  cleanup (e.g. `make clean`) and retry to log your build.
* Make sure that the `CC_LOGGER_GCC_LIKE` environment variable is set correctly
  and contains your compilers. For detailed description see the
  [user guide](analyzer/user_guide.md#log).
* MacOS users need `intercept-build` to be available on the system,
  and in most cases, _System Integrity Protection_ needs to be turned off.
  See the [README](/README.md#mac-os-x) for details.

## Step 2: Analyze your code <a name="step-2"></a>
Once the build is logged successfully (and the `compilation.json`) was created,
you can analyze your project.

1. Run the analysis:
```sh
CodeChecker analyze compilation.json -o ./reports
```
2. View the analysis results in the command line
```sh
CodeChecker parse ./reports
```

Hint:
 You can do the 1st and the 2nd step in one round by executing `check`
```sh
cd tmux
make clean
CodeChecker check -b "make" -o ./reports
```
or to run on 22 threads
```sh
CodeChecker check -j22 -b "make clean;make -j22" -o ./reports
```

### Cross-Compilation <a name="cross-compilation"></a>
Cross-compilers are auto-detected by CodeChecker, so the `--target` and the
compiler pre-configured
include paths of `gcc/g++` are automatically passed to `clang` when analyzing.

**Make sure that the compilers used for building the project (e.g.
`/usr/bin/gcc`) are accessible when `CodeChecker analyze` or `check` is
invoked.**

### Incremental Analysis <a name="incremental-analysis"></a>
The analysis can be run for only the changed files and the `report-directory`
will be correctly updated with the new results.

There are two supported ways for incremental analysis.

a) In case you can build your
project incrementally, you can build, log and analyze only the changed files and all the files
that are depending on the source code changes (in case of the update of a header file).

b) If you only want to re-analyze changed source files, without re-building your
project, you can use skip list to tell CodeChecker which files to analyze.


a) **Using incremental build**

```sh
cd tmux
make clean
CodeChecker check -b "make" -o reports

#Change only 1 file in tmux
vi ./cmd-find.c

#Only cmd-find.c will be re-analyzed
CodeChecker check -b "make" -o reports
```
Since the `make` command only re-compiles the changed `cmd-find.c`
only that file will be re-analyzed.

Now the `reports` directory contains also the results of the updated `cmd-find.c`.

b) **Using skip file**

If you want to re-analyze only the changed source files without build, you
can give a skip-list to CodeChecker.

Let's assume that only `cmd-find.c` that needs to be re-analyzed.

You need to create the following skip list file that tells CodeChecker
to analyze `cmd-find.c` and ignore the rest.
```sh
#skip.list:

+*cmd-find.c
-*
```
Let's assume you have the compilation database in
`compile_commands.json`.

```sh
CodeChecker check ./compile_commands.json -i skip.list -o reports
```
For more details regarding the skip file format see
the [user guide](analyzer/user_guide.md#skip).

c) **Select source files from the compilation database**
You can select which files you would like to analyze from the compilation
database. This is similar to the skip list feature but can be easier to quickly
analyze only a few files not the whole compilation database.

Let's assume you have the compilation database in `compile_commands.json`.

```sh
CodeChecker check ./compile_commands.json -o reports --file "*cmd-find.c"
```

Absolute directory paths should start with `/`, relative directory paths should
start with `*` and it can contain path glob pattern. Example:
`/path/to/main.cpp`, `lib/*.cpp`, `*/test*`.


### Analysis Failures <a name="analysis-failures"></a>

The `reports/failed` folder contains all build-actions that
were failed to analyze. For these there will be no results.

Generally speaking, if a project can be compiled with Clang then the analysis
should be successful always.  We support analysis for those projects which are
built only with GCC, but there are some limitations.

Possible reasons for failed analysis:

* The original GCC compiler options were not recognized by Clang.
* There are included headers for [GCC features which are
  not supported by Clang](analyzer/gcc_incompatibilities.md).
* Clang was more strict when parsing the C/C++ code than the original compiler
 (GCC). Any non-standard compliant or GCC specific code needs to be removed to
 successfully analyze the file. One other solution may be to use the
 `__clang_analyzer__` macro. When the static analyzer is using clang to parse
 source files, it implicitly defines the preprocessor macro
 [__clang_analyzer__](https://clang-analyzer.llvm.org/faq.html#exclude_code).
 One can use this macro to selectively exclude code the analyzer examines.
* Clang crashed during the analysis.

### Avoiding or Suppressing False positives <a name="false-positives"></a>

Sometimes the analyzer reports correct code as incorrect. These findings are
called false positives. Having a false positive indicates that the analyzer
does not understand some properties of the code.

CodeChecker provides two ways to get rid off false positives.

1. The first and the preferred way is to make your code understood by the
analyzer. E.g. by adding `assert`s to your code, analyze in `debug` build mode
and annotate your function parameters. For details please read the
[False Positives Guide](analyzer/false_positives.md).

2. If step 1) does not help, use CodeChecker provided
[in-code-suppression](web/user_guide.md#source-code-comments) to mark
false positives in the source code. This way the suppression information is
kept close to the suspicious line of code. Although it is possible, it is not
recommended to suppress false positives on the Web UI only, because this way
the suppression will be stored in a database that is unrelated to the source
code.

## Step 3: View analysis results in command line or generate static HTML files <a name="step-3"></a>
You can print detailed results (including the control flow) in command line by
running:

```sh
CodeChecker parse --print-steps ./reports
...
Found no defects in grid-view.c
[MEDIUM] /home/ednikru/work/codechecker/play/tmux/log.c:89:1: Opened File never closed. Potential Resource leak [alpha.unix.Stream]
}
^
  Report hash: 88d734fc6eeb71dd292863f2674c370a
  Steps:
    1, log.c:80:6: Assuming 'log_level' is equal to 0
    2, log.c:89:1: Opened File never closed. Potential Resource leak

Found 1 defect(s) in log.c
...
```

It is possible to generate reports as plain `HTML` files using the
`CodeChecker parse` command.
```sh
CodeChecker parse ./reports -e html -o ./reports_html
...
To view the results in a browser run:
> firefox ./reports_html/index.html
```

`./reports_html` directory will contain an `index.html` with a link to all
findings that are stored in separate `HTML` files (one per analyzed build
action).

![Analysis results in static HTML files](images/static_html.png)

Some CodeChecker reports are so easy to fix that even static analyzer tools may
provide automatic fixes on them. In CodeChecker you can list these with the
following command after having analysis reports in `reports` directory:
```sh
CodeChecker fixit --list reports
```

The listed automatic fixes can be applied by omitting `--list` flag. See
`--help` on details of filtering automatic fixes. You can also use the JSON
format output of `CodeChecker cmd diff` command if you want to fix only new
findings:
```sh
CodeChecker cmd diff -b reports1 -n reports2 --new -o json | CodeChecker fixit
```

## Step 4: Store analysis results in a CodeChecker DB and visualize results <a name="step-4"></a>

You can store the analysis results in a central database and view the results
in a web viewer:

1. Start the CodeChecker server locally on port 8555 (using SQLite DB, which is
not recommended for multi-user central deployment) create a workspace
directory, where the database will be stored.

```
mkdir ./ws
CodeChecker server -w ./ws -v 8555
```
A default product called `Default` will be automatically created where you can
store your results.

2. Store the results in the server under run name "tmux" (in the `Default`
product):

```
CodeChecker store ./reports --name tmux --url http://localhost:8555/Default
```
The URL is in `PRODUCT_URL` format:
`[http[s]://]host:port/ProductEndpoint`
Please note that if you start the server in secure mode (with SSL) you will
need to use the `https` protocol prefix.
The default protocol is `http`.
See [user guide](web/user_guide.md#product_url-format) for detailed
description of the `PRODUCT_URL` format.

3. View the results in your web browser
`http://localhost:8555/Default`

## Step 5: Fine tune Analysis configuration <a name="step-5"></a>
### Ignore modules from your analysis <a name="ignore-modules"></a>

You can ignore analysis results for certain files for example 3rd party modules.
For that use the `-i` parameter of the analyze command:
```
 -i SKIPFILE, --ignore SKIPFILE, --skip SKIPFILE
                        Path to the Skipfile dictating which project files
                        should be omitted from analysis. Please consult the
                        User guide on how a Skipfile should be laid out.
```
For the skip file format see the [user guide](analyzer/user_guide.md#skip).

```sh
CodeChecker analyze -b "make" -i ./skip.file" -o ./reports
```

### Enable/Disable Checkers <a name="enable-disable-checkers"></a>

You can list the checkers using the following command
```sh
CodeChecker checkers --details
```
those marked with (+) are enabled by default.

Every supported checker is reported by the `checkers` command and all of its
subcommands.

You may want to enable more checkers or disable some of them using the -e, -d
switches of the analyze command.

For example to enable alpha checkers additionally to the defaults
```sh
CodeChecker analyze -e alpha  -b "make" -i ./skip.file" -o ./reports
```

### Configure Checkers <a name="configure-checkers"></a>

See [Configure Clang Static Analyzer and checkers](analyzer/checker_and_analyzer_configuration.md)
documentation for a detailed description.

### Identify files that failed analysis <a name="identify-files"></a>

After execution of
```sh
CodeChecker analyze build.json -o reports
```
the failed analysis output is collected into `./reports/failed` directory.

This means that analysis of these files failed and there is no Clang Static
Analyzer output for these compilation commands.

## Step 6: Integrate CodeChecker into your CI loop <a name="step-6"></a>

This section describes a recommended way on how CodeChecker is designed to be
used in a CI environment to:

* Generate daily report summaries
* Implement CI guard to prevent the introduction of new bugs into the codebase

In CodeChecker each bug has a unique hash identifier that is independent of
the exact line number therefore resistant to shifts in the source code. With
this feature CodeChecker can recognize the same and new bugs in two different
version of the same source file.

**In summary:**

* Create a single run for each module in each branch and keep it up to date
  with code changes (commits). The CI loop then can compare pull requests
  (commit attempts) against this run and list *new* bugs in the changed code.
  Programmers can also compare their local edits to this run to see if they
  would introduce any new issues.
* Store daily runs of a module every day in a new run post-fixed with date.
* You can query *new* and *resolved* bugs using the
  [`cmd diff`](web/user_guide.md#show-differences-between-two-runs-diff) or the
  Web GUI.
* Programmers should use
  [in-code-suppression](web/user_guide.md#source-code-comments)
  to tell the CI guard that a report is false positive and should be ignored.
  This way your suppressions remain also resistant to eventual changes of the
  bug hash (generated by clang).

### Storing & Updating runs <a name="storing-runs"></a>

Let us assume that you want to analyze your code-base daily and would like to
send out an email summary about any newly introduced and resolved issues.

You have two alternatives:

1. Store the results of each commit in the same run (performance efficient way)
2. Store each analysis in a new run

#### Alternative 1 (RECOMMENDED): Store the results of each commit in the same run <a name="storing-results"></a>

Let us assume that at each commit you would like to keep your analysis
results up-to-date and send an alert email to the programmer if a new bug is
introduced in a "pull request", and if there is a new bug in the
to-be-committed code, reject this "pull request".

A single run should be used to store the analysis results of module on a
specific branch: `<module_name>_<branch>`.

The run should be always updated when a new commit is merged to reflect the
analysis status of the latest code version on your branch.

Let's assume that user `john_doe` changed `tmux/attributes.c` in tmux. The CI
loop reanalyzes `tmux` project and sends an email with reject if new bug was
found compared to the master version, or accepts and merges the commit if no
new bugs were found.

Let's assume that the working directory is `tmux` under the CI job's
_workspace_, that has the source code with John Doe's modifications checked
out.

1. Generate a new log file for the new code
```sh
CodeChecker log -b "make" -o compilation.json
```
2. Re-analyze the changed code of John Doe. If your "master" CI job
```sh
CodeChecker analyze compilation.json -o ./reports-PR
```
3. Check for new bugs in the run
```sh
CodeChecker cmd diff -b tmux_master -n ./reports-PR --new --url http://localhost:8555/Default
```

If new bugs were found, reject the commit and send an email with the new bugs
to John.

If no new bugs were found:

4. Merge the changes into the master branch

5. Update the analysis results according to the new code version:
```sh
CodeChecker store ./reports-john-doe --url http://localhost:8555/Default --name tmux_master
```

If John finds a false positive report in his code and so the CI loop would
prevent the merge of his pull request, he can suppress the false positive by
amending the following suppression comment in his code a line above the bug or
add `assertions` or `annotations` so that the false positive reports are
avoided (see [False Positives Guide](analyzer/false_positives.md)).

An example, as follows:

~~~{.cpp}
int x = 1;
int y;

if (x)
  y = 0;

// codechecker_suppress [core.NullDereference] suppress all checker results
int z = x / y; // warn
~~~

See [User guide](web/user_guide.md#source-code-comments) for more
information on the exact syntax.

Please find a [Shell Script](script_update.md) that can be used
in a Jenkins or any other CI engine to report new bugs.


#### Alternative 2: Store each analysis in a new run <a name="storing-new-runs"></a>

Each daily analysis should be stored as a new run name, for example using the
following naming convention: `<module_name>_<branch_name>_<date>`.

Using `tmux` with daily analysis as example:

1. Generate a new log file
```sh
CodeChecker log -b "make" -o compilation.json
```
2. Re-analyze the project. Make sure you use the same analyzer options all the
   time, as changing enabled checkers or fine-tuning the analyzers *may*
   result in new bugs being found.
```sh
CodeChecker analyze compilation.json -o ./reports-daily
```
3. Store the analysis results into the central CodeChecher server
```sh
CodeChecker store ./reports --url http://localhost:8555/Default --name tmux_master_$(date +"%Y_%m_%d")
```

This job can run daily and will store the results in different runs
identified with the date.

Then you can query newly introduced bugs in the following way.
```sh
CodeChecker cmd diff -b tmux_master_2017_08_28 -n tmux_master_2017_08_29 --new --url http://localhost:8555/Default
```

If you would like to generate a report page out of this using a script, you can get the results in `json` format too:
```sh
CodeChecker cmd diff -b tmux_master_2017_08_28 -n tmux_master_2017_08_29 --new --url http://localhost:8555/Default -o json
```

> **Note:** Don't forget to delete old runs you don't need to save database
> space.

Please find a [Shell Script](script_daily.md) that can be used
in a Jenkins or any other CI engine to report new bugs.

### Gerrit Integration <a name="gerrit"></a>

The workflow based on *Alternative 1)* can be used to implement the gerrit integration with CodeChecker.
Let us assume you would like to run the CodeChecker analysis to *gerrit merge request* and mark the
new findings in the gerrit review.

You can implement that by creating a jenkins job that monitors the
gerrit merge requests, runs the anaysis on the changed files and then uploads the
new findings to gerrit through its [web-api](https://gerrit-review.googlesource.com/Documentation/rest-api.html).

You can find the details and the example scripts in the [Integrate CodeChecker with Gerrit review](jenkins_gerrit_integration.md)
guide.

### Programmer checking new bugs in the code after local edit (and compare it to a central database) <a name="compare"></a>
Say that you made some local changes in your code (tmux in our example) and
you wonder whether you introduced any new bugs. Each bug has a unique hash
identifier that is independent of the line number, therefore resistant to
shifts in the source code. This way, newly introduced bugs can be detected
compared to a central CodeChecker report database.

Let's assume that you are working on the master branch and the analysis of the
master branch is already stored under run name `tmux_master`.

1. You make **local** changes to tmux
2. Generate a new log file
```sh
CodeChecker log -b "make" -o compilation.json
```
3. Re-analyze your code. You are well advised to use the same `analyze`
   options as you did in the "master" CI job: the same checkers enabled, the
   same analyzer options, etc.
```sh
CodeChecker analyze compilation.json -o ./reports
```
4. Compare your local analysis to the central one
```sh
CodeChecker cmd diff -b tmux_master -n ./reports --new --url http://localhost:8555/Default
```

### Setting up user authentication <a name="authentication"></a>
You can set up authentication for your server and (web,command line) clients
as described in the [Authentication Guide](web/authentication.md).

## Updating CodeChecker to new version <a name="upgrade"></a>

If a new CodeChecker release is available it might be possible that there are
some database changes compared to the previous release.
If you run into database migration warnings during the server start please
check our [database schema upgrade guide's](web/db_schema_guide.md)
`Database upgrade for running servers` section.

# Unique Report Identifier (RI) <a name="unique-report-identifier"></a>

Each report has a unique (hash) identifier generated from checker name
and the location of the finding: column number, textual content of the line,
enclosing scope of the bug location (function signature, class, namespace).

You can find more information how these hashes are calculated
[here](analyzer/report_identification.md).

## Listing and Counting Reports <a name="listing-reports"></a>

See a more detailed description in the [analyzer report identification
documentation](analyzer/report_identification.md).

### How reports are counted? <a name="how-report-are-counted"></a>

You can list analysis reports in two ways:

1. Using the **`CodeChecker parse`** command.
2. Reports view of the **Web UI**.

Both of them do **deduplication**: it will not show the same bug report multiple
times even if the analyzer found it multiple times.

You may find the same bug report multiple times for two reasons:

1. The same source file is analyzed multiple times
(because the `compile_commmands.json` contains the build command multiple times)
then the same findings will be listed multiple times.
2. All findings that are found in headers
will be shown as many times as many source file include that header.

**Example:**
```c++
//lib.h:
inline int div_h(){int *p; *p=4;};
inline int my_div(int);
```

```c++
//lib.c:
#include "lib.h"
int my_div(int b){
  return 1/b;
}
```

```c++
//a.c:
#include "lib.h"
int f(){
  return my_div(0);
}
```

```c++
//b.c:
#include "lib.h"
int h(){
  return my_div(0);
}
```

Calling `CodeChecker check --ctu -b "g++ -c ./a.c ./b.c lib.c" --print-steps`
shows:

```
[2018-03-22 10:52] - ----=================----
[HIGH] lib.h:1:30: Dereference of undefined pointer value [core.NullDereference]
inline int div_h(){int *p; *p=4;};
                             ^
  Report hash: 6e7a6b71ac1a26751b7a7f7eea80f5da
  Steps:
    1, lib.h:1:20: 'p' declared without an initial value
    2, lib.h:1:30: Dereference of undefined pointer value

Found 1 defect(s) in lib.c

Found no defects in a.c
[HIGH] lib.c:3:11: Division by zero [core.DivideZero]
  return 1/b;
          ^
  Report hash: fbf28fead62aff104c787906defd1169
  Steps:
    1, b.c:3:17: Passing the value 0 via 1st parameter 'b'
    2, b.c:3:10: Calling 'my_div'
    3, lib.c:2:1: Entered call from 'h'
    4, lib.c:3:11: Division by zero

Found 1 defect(s) in b.c

[HIGH] lib.c:3:11: Division by zero [core.DivideZero]
  return 1/b;
          ^
  Report hash: fbf28fead62aff104c787906defd1169
  Steps:
    1, a.c:3:17: Passing the value 0 via 1st parameter 'b'
    2, a.c:3:10: Calling 'my_div'
    3, lib.c:2:1: Entered call from 'f'
    4, lib.c:3:11: Division by zero

Found 1 defect(s) in a.c

Found no defects in b.c
Found no defects in lib.c

----==== Summary ====----
-----------------------
Filename | Report count
-----------------------
lib.h    |            1
lib.c    |            2
-----------------------
```

These results are printed by doing deduplication and without uniqueing.
As you can see the *dereference of undefined pointer value* error in the
`lib.h` is printed only once, even if the header is included from
`a.c, b.c, lib.c`.

In deduplication mode and without uniqueing (in the Web UI) the reports
in lib.h would be shown only once, as all three findings are identical. So in
total we would see 3 errors: 1 for `lib.h` and 2 for `lib.c`.

In uniqueing mode in the Web UI, only 2 distinct reports would be shown:
1 *dereference of undefined pointer value* for the `lib.h` and 1
`Division by zero` for the `lib.c`.

## Report Uniqueing <a name="report-uniqueing"></a>

There is an additional uniqueing functionality in the
Web UI that helps the grouping findings that have the same
*Report Identifier* within or accross muliple runs.
You can enable this functionality by ticking in the "Unique reports" tick box
in the Bug Overview tab.

This feature is useful when:

* you want to list unique findings accross multiple
runs. In this mode the same report stored in different runs is shown only once.
* you want count reports as one which end up in the same same bug location, but
reached through different paths. For example the same null pointer deference 
error may occur on multiple execution paths.

The **checker statistics** view shows an aggregate count of the reports accross
multiple runs. The report counts shown on that page are calculated using the
unique report identifiers.

## How diffs between runs are calculated? <a name="diffs-between-runs"></a>

Diffs between runs are calculated based on the Unique Report Identifier.

Lets take run *A* and run *B* and take the diff between run *A* and *B*,
where *A* is the baseline.

The base of the comparison are the reports that are not in
*detection status* "Resolved", "Off", "Unavailable" and not in *review status*
"False Positive" and "Intentional".
So all reports that are "active" in the runs.

* Reports only in B (new reports):  
  All reports that have report identifier not present in A and which are in B.

* Reports only in A (old reports):  
  All reports that have report identifier not present in B and which are in A.

* Reports both in A and B (common reports):  
  All reports that have report identifier both in B and A.

`CodeChecker cmd diff` command shows the reports without deduplication and
without uniqueing.

In the Web UI diff view the report list is shown with deduplication and
optionally with uniqueing. Uniqueing can be switched on and off in the UI
by the `Unique reports` tick box.

So `CodeChecker cmd diff` always displays more reports than the Web UI as
duplicates are not filtered out.
