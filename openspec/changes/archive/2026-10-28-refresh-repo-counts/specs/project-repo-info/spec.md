# Spec Delta

## MODIFIED Requirements

### Requirement: Counts never block or break the Projects page
The Projects list SHALL render without waiting for the issue and pull request counts, and SHALL show `--` for them until they arrive. When the counts cannot be read, whether the GitHub CLI is missing, signed out, offline or rate-limited, the affected cells SHALL show `--` and nothing else on the page SHALL change. Counts SHALL be cached for a few minutes so that reloading the page does not query the host again, except that a manual refresh SHALL discard the cached counts so the next read queries the host.

#### Scenario: Table renders before counts
- **WHEN** the user opens the Projects page
- **THEN** every project row is shown immediately, with `--` in Issues and PRs until the counts load

#### Scenario: GitHub CLI unavailable
- **WHEN** the GitHub CLI is not installed or not signed in on the machine running the app
- **THEN** the Issues and PRs cells show `--`, and the Source cell and links still work

#### Scenario: Recent counts are reused
- **WHEN** the user reloads the Projects page shortly after the counts were read
- **THEN** the same counts are shown without a new query to the host

#### Scenario: Manual refresh bypasses the cache
- **WHEN** the user activates the refresh control shortly after the counts were read
- **THEN** the counts are read from the host again rather than reused
