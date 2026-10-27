Feature: Projects and their statistics
  Background:
    Given I signed up as "alice@example.org"
    And I added a GitHub token
    And GitHub has the repository "o/r" with 3 stars
    And the repository has pull requests and issues

  Scenario: Read a project and see its numbers and charts
    When I add the project "o/r"
    And I read the project "o/r" from GitHub
    Then I see "Pull requests"
    And I see "merged"
    And I see "3 of 3 items"
    And all images are loaded
    And the page does not scroll sideways

  Scenario: The dashboard shows a card with a menu for each project
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I open "/dashboard/"
    Then I see "Open pull requests"
    And I see "100% of the data"

  Scenario: Every statistics page shows its data sources
    Given I added the project "o/r"
    When I open "/dashboard/"
    And I click "o/r"
    Then I see "0% of the data"
    When I click "Data and sources"
    Then I see "Data sources"
    And I see "response times: ODS, CSV"

  Scenario: The downloads page shows what was fetched and why
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I click "Downloads" in the menu
    Then I see "Finished"
    And I see "Statistics of o/r"

  Scenario: Build a badge
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I choose "issues" as the badge kind
    And I choose "50" as the badge percentile
    And I choose "bot" as the badge class
    Then the badge markdown contains "kind=issue&percentile=50&class=bot"
    And the badge preview is shown

  Scenario: Contributors and their times in my time zone
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I click "Contributors"
    Then I see "bob"
    And I see "Berlin"
    When I click "bob"
    Then I see the time zone of the browser
    And all images are loaded

  Scenario: Dark and light pages with charts in the same colours
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I choose the dark theme
    Then the page is dark
    And the charts are dark
    When I open "/dashboard/"
    And I click "o/r"
    Then the page is dark
    And the charts are dark
    When I choose the light theme
    Then the page is light
    And the charts are light
