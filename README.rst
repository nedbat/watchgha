########################
Watch GitHub Action runs
########################

This package provides one command, ``watch_gha_runs``.  It takes a GitHub repo
URL and a branch name, and displays the status of the latest GitHub Action runs
on that branch.  If any of the runs are in progress, it will refresh the
display each second with the current status.

Runs are collapsed if all the jobs are successful.  Once all the runs are
completed, the command ends.

I suggest installing with `pipx`_::

    $ pipx install https://github.com/nedbat/watchgha

Now you have a command ``watch_gha_runs`` available.  I use a GitHub alias so
that my current repo and branch are implied::

    [alias]
        runs = "!f() { \
            watch_gha_runs \
                \"$(git remote get-url origin)\" \
                \"$(git rev-parse --abbrev-ref HEAD)\"; \
        }; f"


.. _pipx: https://pypi.org/project/pipx/
