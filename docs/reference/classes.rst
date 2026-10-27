==================
Classes of people
==================

A class has a name, a colour and rules. Somebody who responded belongs to the **first** class, from the top of the list, with a rule that matches. The first response of each class counts, so a bot that answers fast does not hide the first human response.

On the page **Classes**, drag a class by its handle ⠿ to another place, or move it with the arrows. The name and the colour are fields at the top of each class: change them and press **Save**. Each of your classes has its own name.

Kinds of rules
==============

A rule says who belongs to a class: by handle, by a pattern of handles, by the status in the repository, as a bot, by location, or everybody. :doc:`class-rules` lists them, with what each matches and examples.

Default classes
===============

Every account starts with three classes, in this order. They sort everybody, so they cannot be deleted; **Hide** takes one out of the statistics, and it still decides who belongs to it. The author of an issue or pull request never responds to their own item.

.. _class-bot:

bot
---

Bots: accounts GitHub marks as bots, such as ``dependabot[bot]``, and the handle ``coveralls``, as some bots use an account like that of a person. A bot often answers within seconds, so its responses say little about the people of a project. With its own class, the first human response is measured apart from it; hide the class to leave bots out of the charts and tables. The page suggests more accounts that answer like bots, see below.

.. _class-collaborator:

collaborator or higher
----------------------

People with the status *owner*, *member* or *collaborator* in the repository, as GitHub tells it with each comment and review: the people who look after the project. Their first response is what most people mean when they ask how fast a project answers.

.. _class-external:

external
--------

Everybody else: contributors, people who comment for the first time, and users who help each other. The rule *everybody* matches all, so this class comes last and catches whoever no class above took. Its response time shows how much a community answers itself.

.. _shared-statistics:

Shared statistics
=================

Classes of people are not shared: everybody makes their own, and the same pull request can count as answered by a maintainer for one person and by an external contributor for another. So that a shared statistic shows the same numbers to everybody, each class has an id made of its name and a number, such as ``maintainer-3``. The page **Classes** shows it next to each class; only the person who made a class can change it.

When your classes differ from the ones every account starts with, the addresses of your statistics name them: ``?classes=maintainer-3+bot-1+external-7``. People who open the address see the numbers with your classes, in your order, and a note says so with a link back to their own classes. The ids follow a class when it is renamed. An address with a class that was deleted shows an error and the own classes instead. Badges take the same parameter ``classes``.

Suggested bots
==============

The page **Classes** lists accounts that answer like bots: on at least 10 pull requests and issues of others, more than half of their first responses came within 2 minutes, faster than people usually answer. **Add to bot** adds the account to the handles of the first class with the rule *is a bot*. Accounts GitHub marks as bots are not listed; they are in that class already.
