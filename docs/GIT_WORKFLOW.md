# Git Workflow and Branching Strategy

## Overview

This document outlines the Git workflow and branching strategy for the Lab Instrument Control System (LICS) project.

## Branching Strategy

We follow a **Git Flow** branching model with the following branch types:

### Main Branches

#### `main`
- **Purpose**: Production-ready code
- **Protection**: Protected branch, no direct commits
- **Merges**: Only from `release/*` and `hotfix/*` branches
- **Deployment**: Automatically deployed to production
- **Naming**: `main`

#### `develop`
- **Purpose**: Integration branch for features
- **Protection**: Protected branch, no direct commits
- **Merges**: From `feature/*` branches via Pull Requests
- **Testing**: Continuous integration runs on all commits
- **Naming**: `develop`

### Supporting Branches

#### Feature Branches
- **Purpose**: Development of new features or enhancements
- **Branch from**: `develop`
- **Merge to**: `develop` (via Pull Request)
- **Naming convention**: `feature/issue-number-short-description`
- **Examples**:
  - `feature/123-user-authentication`
  - `feature/456-device-management-ui`
  - `feature/789-mqtt-client-implementation`

#### Release Branches
- **Purpose**: Preparation of new releases
- **Branch from**: `develop`
- **Merge to**: `main` and `develop`
- **Naming convention**: `release/version-number`
- **Examples**:
  - `release/1.0.0`
  - `release/1.1.0`
  - `release/2.0.0-beta`

#### Hotfix Branches
- **Purpose**: Critical fixes for production issues
- **Branch from**: `main`
- **Merge to**: `main` and `develop`
- **Naming convention**: `hotfix/issue-number-short-description`
- **Examples**:
  - `hotfix/critical-auth-bug`
  - `hotfix/database-connection-fix`

## Workflow Process

### Feature Development
1. Create feature branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/123-new-feature
   ```

2. Develop and commit changes:
   ```bash
   git add .
   git commit -m "feat: implement new feature functionality"
   ```

3. Push branch and create Pull Request:
   ```bash
   git push -u origin feature/123-new-feature
   ```

4. After review approval, merge to `develop`

### Release Process
1. Create release branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/1.0.0
   ```

2. Perform final testing and bug fixes
3. Update version numbers and changelog
4. Merge to `main` and tag:
   ```bash
   git checkout main
   git merge --no-ff release/1.0.0
   git tag -a v1.0.0 -m "Release version 1.0.0"
   ```

5. Merge back to `develop`:
   ```bash
   git checkout develop
   git merge --no-ff release/1.0.0
   ```

### Hotfix Process
1. Create hotfix branch from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/critical-bug-fix
   ```

2. Fix the issue and test
3. Merge to `main` and tag:
   ```bash
   git checkout main
   git merge --no-ff hotfix/critical-bug-fix
   git tag -a v1.0.1 -m "Hotfix version 1.0.1"
   ```

4. Merge to `develop`:
   ```bash
   git checkout develop
   git merge --no-ff hotfix/critical-bug-fix
   ```

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

### Examples
```
feat(auth): add JWT token validation
fix(device): resolve MQTT connection timeout
docs(api): update device registration endpoint
style(frontend): apply consistent code formatting
refactor(backend): extract database connection logic
test(edge-agent): add unit tests for sensor controller
chore(deps): update dependencies to latest versions
```

## Pull Request Guidelines

### Requirements
- [ ] Branch is up to date with target branch
- [ ] All CI checks pass
- [ ] Code review approval from at least one team member
- [ ] Documentation updated if necessary
- [ ] Tests added or updated for new functionality

### PR Title Format
Use the same convention as commit messages:
```
feat(scope): brief description of changes
```

### PR Description Template
```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No console errors
- [ ] Follows coding standards
```

## Branch Protection Rules

### Main Branch
- Require pull request reviews before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Restrict pushes that create files larger than 100MB
- Require linear history

### Develop Branch
- Require pull request reviews before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging

## Best Practices

1. **Keep branches focused**: One feature or fix per branch
2. **Regular updates**: Sync with develop regularly to avoid conflicts
3. **Atomic commits**: Each commit should represent a single logical change
4. **Descriptive messages**: Write clear, descriptive commit messages
5. **Test before merge**: Ensure all tests pass before creating PR
6. **Code review**: All code should be reviewed before merging
7. **Clean history**: Use squash merging for feature branches when appropriate

## Emergency Procedures

### Production Hotfix
1. Immediately create hotfix branch from `main`
2. Fix the critical issue with minimal changes
3. Test the fix thoroughly
4. Fast-track the review process
5. Deploy immediately after merge
6. Post-mortem analysis after resolution

### Rollback Procedure
1. Identify the problematic commit/release
2. Create hotfix branch from last known good state
3. Revert changes or apply specific fixes
4. Follow standard hotfix process
5. Update monitoring and alerts