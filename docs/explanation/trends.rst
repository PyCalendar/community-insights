=============
Read trends
=============

The page **Trends** of a project shows whether more or less happens: issues on one side, pull requests on the other. Each number of the time range stands next to the same number of the time just before it, and charts show it per day, week or month. This page explains what is counted.

The time range and the time before
==================================

Choose the time range at the top of the page: **Last 7 days**, **Last 30 days** or **Last 90 days**, or **From** and **To** for any dates. Every number is compared with the time of the same length that ends where the time range starts: the last 30 days with the 30 days before them, 1 to 14 March with 15 to 28 February. The page names the days of the time before.

All time has nothing before it, so the page shows the numbers without a change. The same holds for a time range with only **To**.

The page shows the change as a share of the time before, such as *+25 %* when 12 became 15. When the time before had none, the change is the number itself, such as *+3*.

What is counted
===============

opened
    The issues or pull requests opened in the time range, also those of bots, as on **Overview**.
closed
    The issues closed in the time range, whenever they were opened. For pull requests, **closed without merging**: those closed in the time range that were not merged.
merged
    The pull requests merged in the time range. A merged pull request is not counted as closed, so the two numbers add up to all pull requests that ended in the time range.
contributions
    Openings, comments and reviews on issues or on pull requests by people, not bots. Below the number, how many people made them. See :ref:`contributions`.
new contributors
    The people, not bots, whose first contribution to issues, or to pull requests, is in the time range. They are listed by name under the charts. A person who opened an issue last year and their first pull request today is a new contributor to pull requests, but not to issues. Handles are compared without case, as on GitHub.

Bots are who GitHub marks as one, and handles that end with ``[bot]``.

.. _contributions:

What a contribution is
======================

A contribution is one of these, by a person and not by a bot:

- opening an issue or a pull request,
- a comment on an issue or a pull request, also a comment on a line of code,
- a review of a pull request, also an approval without a comment.

These are not contributions on this page:

- **Commits** do not count. A commit belongs to no issue or pull request until it is in one, and the same commit can be in several pull requests. The pull request that holds the commits counts once, when it is opened. The page **Contributors** has the commits of each person.
- Reactions, labels, assignments and other changes of an issue or a pull request.
- Closing or merging. These are counted as **closed** and **merged** instead.
- The work of bots, such as a service that updates dependencies or runs the tests.

**Contributors** are the people who made at least one contribution. Somebody who comments ten times is ten contributions and one contributor.

New contributors are new to what the site has read
==================================================

The site only knows what it read from GitHub. A person is new when the site has no earlier contribution of theirs to these repositories. Read the whole history before trusting the new contributors: the bar at the top of the page shows how complete the data is. A project of several repositories counts the first contribution to any of them.

The charts
==========

Each side has two charts: opened and closed (for pull requests opened, closed without merging, and merged), and contributions and new contributors. Without a start of the time range, the charts start with the first issue, pull request or contribution. Days start at midnight in your time zone, shown at the bottom of the page.

.. _bars:

The length of the bars
----------------------

**Bars of the charts** chooses how long a bar is: days, calendar weeks, months or years. **Automatic** takes the shortest that splits the time range into at most 31 bars:

========================  ======================
time range                a bar is
========================  ======================
a week, a month           a day
two months, half a year   a calendar week
a year, two years         a month
five years                a year
========================  ======================

So a chart has at least 4 bars where the time range allows it. Three years from a day in November are 37 months, too many, and so 4 years, of which the first and the last are parts. A choice that would make more than 400 bars, such as days for ten years, is replaced by the automatic one.

Weeks are calendar weeks after ISO 8601: they start on Monday, and week 1 is the week with the first Thursday of the year. The label *CW 1 2026* (*KW* in German) is the week from Monday, December 29, 2025 to Sunday, January 4, 2026. The first and the last bar can be a part of a day, week, month or year: the part of it that is inside the time range.

The length of the bars also is the unit of the statistical trend: *per day*, *per week*, *per month* or *per year*.

.. _statistical-trend:

The statistical trend
=====================

Comparing a time range with the time before says whether two numbers differ, not whether they differ by more than chance. Under the charts of each side, **Statistical trend** answers this for the contributions and for the contributors: do they really grow or shrink in the time range, by how much, and how sure is that?

What the page says
------------------

For example: *Contributions grow by 12 % per week, with an error margin of ±8 percentage points: the 95 % confidence interval is +4 % to +20 %. The fitted line goes from 21.3 to 41.9 per week over 7 bars. Statistically significant (p = 0.0040, below 0.05): a change this big would be unlikely without a real trend.*

grow by, shrink by
    How much the count changes from one bar to the next, on average over the time range: 12 % per week means that each week has 1.12 times the contributions of the week before.
error margin, confidence interval
    How exact the 12 % is. The data cannot tell the true growth exactly; with 95 % confidence it is in the interval, here between 4 % and 20 % per week. The error margin is half the width of the interval. Few bars, few contributions or counts that jump up and down make the interval wide.
fitted line
    The count that the trend expects for the first and for the last bar. It shows how big the change is over the whole time range: here the contributions about doubled.
statistically significant, p-value
    The p-value is the probability of a change this big or bigger if, in truth, the count did not change and only chance made it go up and down. Below 0.05 (5 %), the page calls the trend statistically significant: chance alone would rarely do this. Otherwise it says that the trend is not significant: the change may be chance even when it looks large, and the confidence interval includes 0 %, so the data cannot tell growth from shrinking.

*Too little data for a trend* means fewer than 4 bars, fewer than 5 contributions (or contributors) in all, or all of them in one bar. Choose a longer time range or shorter bars.

Why a trend and not only the time before
----------------------------------------

The cards compare two numbers: this month and the month before. One busy week, a release or a holiday changes them a lot. The trend uses every bar of the time range, so a single busy bar has less weight, and it says how sure the change is. The two can disagree: +40 % against the time before with a trend that is not significant means that the difference is within what chance makes.

How the data comes about
------------------------

The counts are those of the chart **Contributions and new contributors**: each bar counts the contributions (see :ref:`contributions`) made in it, and the contributors: the people who made at least one contribution in it, each once. A person who contributes every week counts in every week. The bars are in your time zone, so a contribution late in the evening is on the day you would expect.

What a trend does not say
-------------------------

- It describes the time range, not the future. A significant growth says that the counts grew, not that they keep growing.
- It does not say why. A new release, a conference, a bot that was left out or a move of the project to GitHub all change the counts.
- Weekdays matter. Contributions drop at weekends, so a trend per day over a range that ends on a Saturday leans down. Calendar weeks or months avoid this.
- The data is as complete as the site has read it: the bar at the top of the page shows how complete.
- Being significant is not being large. With many contributions, a growth of 1 % per month can be significant and still be too small to matter. Read the change and its interval, not only the verdict.

The model, for statisticians
----------------------------

This section gives the exact method, so that it can be checked. The code is ``community_insights/stats/count_trend.py``; the counts per bar come from ``stats/kind_series.py`` and ``stats/periods.py``.

Model
    For the bars :math:`i = 0, 1, \ldots` with counts :math:`y_i` and exposure :math:`e_i \in (0, 1]` (the part of the bar inside the time range), a generalized linear model with a Poisson family and a log link:

    .. math::

       \log \mathrm{E}[y_i] = \log e_i + \beta_0 + \beta_1 i

    fitted by iteratively reweighted least squares (``statsmodels.api.GLM(y, add_constant(i), family=Poisson(), exposure=e)``). Bars without any time in the range (:math:`e_i = 0`) are left out.
Reported change
    :math:`100 (e^{\beta_1} - 1)` percent per bar; the ends of the interval are transformed the same way, so the interval is not symmetric around the estimate, and the error margin shown is half its width. The fitted line is :math:`e^{\beta_0 + \beta_1 i}` at the first and the last bar.
Overdispersion
    Counts of contributions are overdispersed: a single discussion brings many comments. The dispersion is estimated by Pearson's statistic, :math:`\hat\phi = \max\left(1, \frac{1}{n - 2} \sum_i \frac{(y_i - \hat\mu_i)^2}{\hat\mu_i}\right)`, and the covariance of the Poisson fit is multiplied by it (quasi-Poisson; the estimates of :math:`\beta` are those of the Poisson fit). The floor at 1 keeps underdispersed data, such as counts on an exact exponential curve, from narrowing the interval below that of a Poisson process.
Interval and test
    A Wald interval and test of :math:`\beta_1 = 0` with the scaled standard error, against Student's *t* with :math:`n - 2` degrees of freedom (``fit(scale=phi, use_t=True)``), because :math:`\hat\phi` is estimated from as few as 4 bars. The test is two-sided; significant means :math:`p < 0.05`.
Contributors
    The number of distinct people per bar is fitted with the same model. It is not a sum of independent events, so the Poisson family is an approximation; the dispersion estimate absorbs part of the difference. A count of distinct people in a partial bar does not scale exactly with its exposure either.
Assumptions
    The bars are independent given the trend, and the trend is log-linear over the time range. Autocorrelation (busy weeks follow busy weeks) makes the interval too narrow; seasonality (weekdays, holidays) is not modelled. No correction is made for testing two counts on two sides of the page.
Limits
    Fewer than 4 bars with time in the range, a total below 5, or counts in fewer than 2 bars give no trend: with counts in one bar only, the maximum likelihood estimate of :math:`\beta_1` does not exist (it diverges). Counts that are the same in every bar (after exposure) give a change of 0 % and :math:`p = 1` without a fit.
Tests
    ``tests/statistics/test_count_trend.py`` checks a steady growth, no change, overdispersion that widens the interval, the floor of the dispersion, partial bars and the cases without a trend.
