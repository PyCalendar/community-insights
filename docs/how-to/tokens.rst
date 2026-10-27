==========================
Add GitHub tokens
==========================

Data is read from GitHub with your linked GitHub account and with tokens, in the order shown on **GitHub access**. GitHub allows 5000 API points per hour for each account. When one is used up, the next one is used, so more tokens read faster. Friends can give you a token of theirs, too.

Create a token
==============

#. Open `new fine-grained token <https://github.com/settings/personal-access-tokens/new>`_ on GitHub.
#. Give it a name and an **expiration date**. Some organisations, such as Plone, refuse tokens that never expire; their repositories cannot be read with such a token. The site warns you about tokens without expiry and 14 days before one expires.
#. Choose the resource owner: yourself, or an organisation that allows tokens.
#. Repository access: public repositories need no permissions. For private repositories choose them and give read-only access to **Pull requests**, **Issues** and **Metadata**.
#. Create the token and copy it.

A classic token works, too: no scopes for public repositories, ``repo`` for private ones.

Add it
======

#. Open **GitHub access**, paste the token and give it a name such as *from Kim*.
#. Set the two sliders (see below).
#. Press **Test on my projects**: it tells you which repositories of your projects the token cannot read.
#. Use the arrows to change the order. The first token that has points left is used.

Share points
============

Each token has two sliders:

**Maximum points to use per hour**
    0 to 100 % of the points GitHub gives the token per hour, shown as *4500 of 5000 points per hour, stopping when 500 are left*. The rest stays with GitHub, for whatever else the token is used for; the site does not use the token when GitHub reports fewer points left than that.

**Free for everybody else on this site**
    0 to 100 % of that maximum, 10 % by default: 500 of 5000 points. Other people on this site use these points after their own tokens. They are a part of the maximum, so lowering the maximum lowers them, too.

Your own tokens are used first, then the points others share. Points used by others are counted on their own, so you can see them.

When the points are not enough
==============================

The fetch page shows how many points are left this hour, of your tokens and shared by others, and how many a full fetch needs. If they are not enough, it says so and asks how many more points of your tokens are fine for this hour. Those are used above the maximum of your tokens until an hour later. A fetch that runs out of points waits until GitHub renews them and goes on; nothing that was read is lost.

A fetch that needs more than 5000 points asks for a limit for the whole fetch; the limit you usually want is set under **Profile**.

Without a token
===============

People who have no token yet can still read public repositories: the site then uses GitHub without a token, which allows 60 requests per hour for the address of the server, shared by everybody on it. That is enough for a few small repositories. Reviews without a comment and the names and locations of people cannot be read that way.
