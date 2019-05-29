# Development Workflow

This document provides a rough overview of the contents of `devops/` and some of the other scripts in the root of the repository, including how these various utilities should be used and what they do to improve the development workflow.

## Use Cases

### Pre-Development

| Need | Command | Notes |
| --- | --- | --- |
| Set up a fresh environment (assuming dependencies are installed) | `./prepare_ci_env.sh` then `source prepare_python_env.sh` | See [Confluence](todo: link) for help with dependencies depending on OS |
| Start or restart the core application | `./axonius.sh system up --restart` |  |
| List available adapters | `./axonius.sh ls` |  |
| Have other useful utilities added to your `$PATH` | `source devops/devops.rc` | Do this before any development! |



### During Development

| Need | Command | Notes |
| --- | --- | --- |
| Create a new Adapter | `create_adapter.py NAME` | The resulting skeleton will have the string `AUTOADAPTER` for you to replace in various places |
| Start a specific adapter | `./axonius.sh adapter NAME up` | The core application should be up already, and another instance of the same adapter cannot be up |
| Stop a specific adapter | `./axonius.sh adapter NAME down` |  |
| See Docker logs for an adapter that failed to start | See `logs/NAME-adapter/NAME_adapter.docker.log` | TODO: mention log parsing utilities? |
| See application logs for an adapter once running | See `logs/NAME-adapter/NAME_adapter_0.axonius.log` | TODO: mention log parsing utilities? |
| Reload the frontend | `./axonius.sh service gui up --restart` `--hard --yes-hard` | Won't reload images |
| Rebuild/reload the frontend completely | `./axonius.sh service gui up --restart` `--hard --yes-hard --rebuild --rebuild-libs` |  |
| Skip tests for a specific adapter | `auto_skipper.py --adapter NAME --ticket TICKET` | Ticket is optional |

### Post-Development/Release

| Need | Command | Notes |
| --- | --- | --- |
| TODO |  |  |

### Special/One-Off

| Need | Command | Notes |
| --- | --- | --- |
| TODO |  |  |

## Notes

- This is incomplete and may have mistakes as it's based @dantrauner's experience getting started. Others should contribute (but try to really keep it to an MVP, linking out to other documentation/READMEs when possible)
- Avoid linking to Confluence for things that are very specific to development/code and would make more sense as a README within the repository (better to link from a Confluence page to the READMEs if really necessary, or even better, autogenerate a Confluence page using CI based on the README files in this repository :smile:)