from .item_filter import ItemFilter


class PersonItemFilter(ItemFilter):
    """The filters of the pull requests and issues of one person: without the author."""

    def __init__(self, *args, **kwargs):
        """The filters of ItemFilter, but the author is the person of the page.

        Args:
            *args: The arguments of ItemFilter.
            **kwargs: Its keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.filters.pop("author")
