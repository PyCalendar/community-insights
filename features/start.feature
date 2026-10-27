Feature: Start page
  People who are not signed in learn what the site does and can sign up.

  Scenario: The start page offers to sign up
    When I open "/"
    Then the title is "Contributor Community Insights"
    And I see "Sign up with email"
    And the page does not scroll sideways

  Scenario: The footer links to the about page and to bug reports
    When I open "/"
    Then the footer links to "About"
    And the footer links to "Report a bug"
    And the link "Report a bug" goes to "https://github.com/PyCalendar/community-insights/issues/new"

  Scenario: The about page shows the version and the licenses
    When I open "/about/"
    Then I see "Version"
    And I see "Django"
    And I see "Bootstrap"

  Scenario: The time zone of the browser is sent to the server
    When I open "/"
    Then the site shows times in the time zone of the browser

  Scenario: Switch the language in the footer
    When I open "/"
    And I click "Deutsch"
    Then I see "Noch kein Repository"
    When I click "English"
    Then I see "No repository yet"
