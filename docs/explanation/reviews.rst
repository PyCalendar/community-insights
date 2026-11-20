=======
Reviews
=======

The page **Reviews** of a project shows how many reviews the pull requests got, who gave them, of which kind, whether there are more or fewer of them over time, and how many reviews a pull request had until it was merged. This page explains what is counted, and how.

What a review is
================

A review is what GitHub calls one: on a pull request, **Review changes** with one of

approved
    The reviewer approves the pull request.
changes requested
    The reviewer asks for changes before it can be merged.
commented
    The reviewer comments without approving or asking for changes, also a comment on a line of code that is part of a review.

A review that was dismissed later, and a review read before the site read the kinds, count as **dismissed or unknown**. The kinds are read with the pull requests; those read before are read again once.

These are not reviews: a comment in the conversation of the pull request (see :ref:`contributions`), a review by the author of the pull request (such as an answer to a comment on a line), and reviews of bots.

Collaborators and others
========================

GitHub gives each reviewer a status in the repository at the time of the review. **Collaborators** are the owners, members of the organisation and collaborators: the people who may merge. **Others** are contributors, first-time contributors and people without a status: reviews from outside. A person who becomes a member counts as a collaborator for the reviews after that.

The numbers
===========

The cards show the reviews of the time range, by collaborators and by others, each next to the time of the same length just before, as on :doc:`trends`. *Reviews by 3 people* counts the people who gave them.

**Kinds of review** shows the reviews of the time range by their kind, by collaborators and by others, as a chart and a table.

**Reviews until merged** takes the pull requests merged in the time range and counts the reviews each had before it was merged; reviews after the merge are left out. The chart shows how many pull requests had 0, 1, 2, 3, 4, or 5 and more reviews. The text gives the median (half of the pull requests had fewer, half more), the mean, and how many were merged without any review.

Reviews over time and the trend
===============================

**Reviews over time** shows the reviews by collaborators and by others per day, calendar week, month or year, chosen as on :doc:`trends` (:ref:`bars`).

Under it, **Statistical trend** tells for all reviews, for those of collaborators and for those of others, first whether there is a significant trend, and then how much the count grows or shrinks per bar, with its error margin, its 95 % confidence interval and its p-value. *No significant trend* means the change may be chance: the interval holds 0 %.

The model is the same as for the contributions on **Trends**: a quasi-Poisson regression of the reviews per bar, with the part of each bar inside the time range as its exposure, the dispersion estimated from the data (at least that of a Poisson process), and Student's *t* with :math:`n - 2` degrees of freedom. :ref:`statistical-trend` explains it and gives the formulas to check it.

For reviews, keep in mind:

- Reviews come in groups: a pull request often gets several reviews in a day, and a release brings many. This spreads the counts more than chance, and the model widens the interval for it.
- A trend of reviews follows the pull requests: fewer pull requests mean fewer reviews. Compare it with the trend of pull requests on **Trends** before reading it as more or less reviewing per pull request.
- Whether a reviewer is a collaborator is taken at the time of the review, so new maintainers move reviews from others to collaborators over time.
