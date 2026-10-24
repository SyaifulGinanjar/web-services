import math

from flask import current_app, request


class Page:
    """Hasil query yang sudah dipaginasi."""

    def __init__(self, items, total, page, per_page):
        self.items = items
        self.total = total
        self.per_page = per_page
        self.pages = max(1, math.ceil(total / per_page)) if per_page else 1
        self.page = min(max(1, page), self.pages)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def first_index(self):
        return 0 if self.total == 0 else (self.page - 1) * self.per_page + 1

    @property
    def last_index(self):
        return min(self.page * self.per_page, self.total)

    def iter_pages(self, edge=1, around=2):
        """Nomor halaman dengan None sebagai penanda '…'."""
        last = 0
        for num in range(1, self.pages + 1):
            if num <= edge or num > self.pages - edge or abs(num - self.page) <= around:
                if last and num - last > 1:
                    yield None
                yield num
                last = num


class ListParams:
    """Parameter list dari query string: q, page, per_page, sort, dir + filter tambahan."""

    def __init__(self, sortable, default_sort, default_dir='asc', filters=()):
        args = request.args
        cfg = current_app.config

        self.q = (args.get('q') or '').strip()[:100]
        self.page = _to_int(args.get('page'), 1)

        per_page = _to_int(args.get('per_page'), cfg['PER_PAGE_DEFAULT'])
        self.per_page = per_page if per_page in cfg['PER_PAGE_OPTIONS'] else cfg['PER_PAGE_DEFAULT']

        sort = args.get('sort')
        self.sort = sort if sort in sortable else default_sort
        self.sort_column = sortable[self.sort]

        direction = (args.get('dir') or default_dir).lower()
        self.dir = direction if direction in ('asc', 'desc') else default_dir

        self.filters = {name: (args.get(name) or '').strip() for name in filters}

    @property
    def offset(self):
        return (self.page - 1) * self.per_page

    @property
    def order_by(self):
        # Kolom sudah di-whitelist lewat `sortable`, aman dipakai di SQL
        return f'{self.sort_column} {self.dir.upper()}'

    @property
    def like(self):
        escaped = self.q.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')
        return f'%{escaped}%'


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
