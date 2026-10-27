Feature: Accounts and GitHub access
  People sign up with an email address and give access to GitHub with tokens.

  Scenario: Somebody new is asked for GitHub access
    Given I signed up as "alice@example.org"
    Then I see "link your GitHub account or add a personal access token"

  Scenario: A token gives access to GitHub and my repositories
    Given I signed up as "alice@example.org"
    And GitHub has the repository "alice/tool" with 7 stars
    When I add a GitHub token
    And I open "/dashboard/"
    And I click "Add repositories"
    And I click "Refresh from GitHub"
    And I choose "alice/tool" from my repositories
    Then I see "alice/tool was added."
    And I do not see "link your GitHub account"

  Scenario: A token without expiry is warned about
    Given I signed up as "alice@example.org"
    When I add a GitHub token
    Then I see "organisations such as Plone refuse"

  Scenario: Test a token on my projects
    Given I signed up as "alice@example.org"
    And I added a GitHub token
    And GitHub has the repository "o/r" with 1 stars
    And GitHub has the repository "o/secret" with 1 stars
    And I added the project "o/r"
    And I added the project "o/secret"
    And the token cannot read "o/secret"
    When I open "/dashboard/github/"
    And I click "Test on my projects"
    Then I see "cannot read 1 of 2 repositories: o/secret"

  Scenario: The menu works on any screen
    Given I signed up as "alice@example.org"
    When I click "Classes" in the menu
    Then I see "Classes of people"
