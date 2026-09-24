# Workspace migration

This release installs into `.drobotics-x5/`. S and X5 use separate sibling directories `.drobotics-s/` and `.drobotics-x5/`.

Run `bash setup.sh --update <project-root>` from the new release. The installer refreshes its recognized routing blocks in existing AGENTS.md and CLAUDE.md. User rules are retained.

Legacy workspaces (`.horizon/` for S, `.drobotics/` for X5) remain untouched. Review and migrate board/environment configuration before running tasks; recreate virtual environments at the new path rather than moving them. Do not copy old Skill code over the new release.

As before, `--update --force` rebuilds only this pack's new workspace. Back up changes made inside that managed directory before forcing an update.
