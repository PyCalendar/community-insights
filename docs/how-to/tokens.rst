==========================
Add GitHub tokens
==========================

Data is read from GitHub with your linked GitHub account and with tokens, in the order shown on **GitHub access**. GitHub allows 5000 API points per hour for each account. When one is used up, the next one is used, so more tokens read faster. Friends can give you a token of theirs, too.

Create a token, step by step
============================

This example creates a token that reads public repositories for 90 days. It takes about two minutes.

#. Sign in to GitHub and open `new fine-grained token <https://github.com/settings/personal-access-tokens/new>`_. GitHub reaches this page through *Settings*, *Developer settings*, *Personal access tokens*, *Fine-grained tokens*, *Generate new token*.
#. **Token name**: a name that says where the token is used, such as ``community-insights``.
#. **Description** (optional): such as ``Reads public repositories for Contributor Community Insights``.
#. **Resource owner**: your own account. Choose an organisation only for its private repositories, and only if it allows tokens.
#. **Expiration**: 90 days. Some organisations, such as Plone, refuse tokens that never expire; their repositories cannot be read with such a token. The site warns you about tokens without expiry and 14 days before one expires.
#. **Repository access**: *Public repositories*. Public repositories need no permissions, so leave all of them at *No access*.

   For private repositories, which an installation reads only when it allows them, choose *Only select repositories* and give read-only access to **Pull requests**, **Issues** and **Metadata**.
#. Press **Generate token**. GitHub shows the token once. It looks like this example, which is made up and does not work:

   .. code-block:: text

       github_pat_11AEXAMPLE0ab12CD34ef_5678ghIJ90klMNopQRstUVwxYZ1234567890abcdEFGHijklMNOPqrstUV

#. Copy the token. Do not save it anywhere else: you can always create a new one.

A classic token works, too: no scopes for public repositories, ``repo`` for private ones.

Add the token to the site
=========================

#. Open **GitHub access** in the menu.
#. Under **2. Tokens**, paste the token into **Token** and give it a name, such as *from Kim* for a token a friend gave you.
#. Set the two sliders, see :ref:`share-points`.
#. Press **Add the token**. The site asks GitHub who the token belongs to, how many points it has and when it expires, and shows that in the list.
#. Press **Test on my projects**: it tells you which repositories of your projects the token cannot read. The made up demo project is not tested.
#. Drag a token by its handle ⠿ to another place, or use the arrows, to change the order. The first token that has points left is used.

.. _share-points:

Share points
============

Each token has two sliders:

**Maximum points to use per hour**
    0 to 100 % of the points GitHub gives the token per hour, shown as *4500 of 5000 points per hour, stopping when 500 are left*. The rest stays with GitHub, for whatever else the token is used for; the site does not use the token when GitHub reports fewer points left than that.

**Free for everybody else on this site**
    0 to 100 % of that maximum, 10 % by default: 500 of 5000 points. Other people on this site use these points after their own tokens. They are a part of the maximum, so lowering the maximum lowers them, too.

Your own tokens are used first, then the points others share. Points used by others are counted on their own, so you can see them.

Points and limits
=================

GitHub counts what a token reads in points. One request reads 50 pull requests or issues with their comments and reviews and costs about one point; items with many comments and the profiles of the people cost a few more. Every account and every token gets 5000 points per hour. The site estimates the points of a fetch before it starts, from the number of pull requests and issues of the repositories.

When the points are not enough
==============================

The fetch page shows how many points are left this hour, of your tokens and shared by others, and how many a full fetch needs. If they are not enough, it says so and asks how many more points of your tokens are fine for this hour. Those are used above the maximum of your tokens until an hour later. A fetch that runs out of points waits until GitHub renews them and goes on; nothing that was read is lost.

A fetch that needs more points than the **Suggested limit of API points** under **Profile** on **GitHub access** asks for a limit for the whole fetch: the most points it may use, and proposes that number. At first it is 5000, the points of one account in one hour; for visitors it is always 5000. When the limit is reached, the fetch stops and keeps what it read; start it again to read more.

Without a token
===============

People who have no token yet can still read public repositories: the site then uses GitHub without a token, which allows 60 requests per hour for the address of the server, shared by everybody on it. That is enough for a few small repositories. Reviews without a comment and the names and locations of people cannot be read that way.
