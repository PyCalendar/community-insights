=========================
Read the response times
=========================

The overview of a project shows how long pull requests and issues waited for their first response, for each class of people. **Statistic** chooses how these times are summed up: *measured*, *normal*, *exponential* or *Kaplan-Meier*. This page explains what each one shows and when to trust it. :doc:`../how-to/verify` shows how to compute the same numbers yourself.

What is counted
===============

A response is a comment or a review by somebody other than the author of the pull request or issue. For each item, the site takes the first response of each class of people (see :doc:`../reference/classes`): the first response of a bot does not hide the first response of a maintainer. The time is from the creation of the item to that response.

Some items never got a response of a class: they were closed without one, or they still wait. The statistics treat them differently, see below.

The columns
===========

class
    The class of people who responded.
n
    How many items are counted. For *measured*, *normal* and *exponential* these are the items with a response of the class. For *Kaplan-Meier* these are all items, also those without a response, so its n is the same for every class.
average
    The mean of the times. A few very long waits pull it up a lot.
std error
    The standard error of the average: how much the average would change with other items of the same kind. Roughly, the true average lies within two standard errors of the one shown. Fewer items give a bigger standard error.
median
    Half of the responses came faster than this, half slower. Long waits do not pull it up, so it says more about a typical item than the average.
95%
    95 of 100 responses came within this time: the time to promise when you want to keep the promise almost always.

The statistics
==============

Measured
--------

The times as they are: the average, the median and the 95th percentile of the items that got a response, without a model. This is the most direct view, and what a badge shows unless it names another model.

It leaves out the items without a response. When many items wait or were closed without an answer, the measured times look faster than the project is: the slowest cases are missing.

Normal
------

A bell curve fitted to the times: most responses near the average, as many faster as slower. Its median is its average, and its 95% is the average plus 1.645 standard deviations.

Response times are rarely like that: many come within hours, a few take weeks. The normal fit then puts the median too high and can even need negative times to balance the long waits. Use it only when the times gather around a typical value, such as a team that answers every morning.

Exponential
-----------

The waiting time when an answer is equally likely in every hour that passes, like waiting for a bus that comes at random. It has one number, the average; the median is about 0.69 times the average and the 95% about three times the average.

It fits many projects better than the normal one: many fast responses and fewer and fewer slow ones. When it is far from the measured median, the times have another shape, such as fast bots and slow people in the same class.

Kaplan-Meier
------------

The only statistic that also counts the items without a response. Such an item says: the response took at least as long as the item was watched, until it was closed or until now. Kaplan-Meier uses this to estimate which share of items gets a response within each time, as used for survival times in medicine.

It shows the median and the 95%. A ``-`` means that this share never got a response of the class: when only 40 of 100 items got an answer from a maintainer, there is no time by which half of them did. It has no average and no standard error, as the longest waits are not known.

Use it when many items wait or were closed without an answer: it honestly answers how long it takes until an item is answered.

Which one to look at
====================

A badge uses *measured* unless its parameter ``model`` names another one (see :doc:`../reference/badges`); the badge builder on the overview has the same choice.

The page first shows the fit with the lowest standard error, summed over the classes: the one whose average is the most certain. That is a choice of precision, not of truth, so compare:

- *Measured* and *Kaplan-Meier* close together: few items lack a response, the measured times are fine.
- *Kaplan-Meier* much slower, or ``-``: many items are not answered; the measured times flatter the project.
- *Exponential* close to *measured*: the times have the usual shape; its 95% is a sound promise.
- *Normal* very different from *measured*: ignore *normal* for this project.

Example
-------

Four pull requests got their first maintainer response after 1 minute, 2 minutes, 10 minutes and 1 hour; a fifth is open for a week without one. *Measured* says a median of 6 minutes, from the four answered ones. *Kaplan-Meier* counts all five: three of five were answered within 10 minutes, so its median is 10 minutes, and its 95% is ``-``, as one in five was never answered.
