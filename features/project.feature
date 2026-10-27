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

  Scenario: Write a query with the names of the variables and run it with Enter
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I click "Contributors"
    And I type "prs_mer" into the query
    Then the query suggests "prs_merged"
    When I press Tab in the query
    Then the query is "prs_merged "
    When I type ">= 0" into the query
    And I press Enter in the query
    Then the address has the query "prs_merged >= 0"
    And I see "people"

  Scenario: Choose the columns of the contributors
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I click "Contributors"
    And I remove the column "user_location"
    And I move the column "user_class" left
    And I add the column "activity_total"
    And I click "Run the query"
    Then the table has the columns "user_class user_handle" first
    And the table has no column "user_location"
    And I see "activity_total"

  Scenario: Share a chart with the page it comes from
    Given I added the project "o/r"
    And I read the project "o/r" from GitHub
    When I click "Share this chart"
    Then I see "Share a chart"
    And the code to share in Markdown contains "chart/responses-pr.svg"
    And the code to share in reStructuredText contains ":target: http"
    And all images are loaded

  Scenario: The colours of the page are chosen from a menu with an icon
    Given I open "/about/"
    When I choose the dark theme
    Then the theme switch shows "☾"
    When I choose the auto theme
    Then the theme switch shows "◐"
