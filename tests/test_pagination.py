from app.pagination import ListParams, Page

SORTABLE = {'nama': 'c.nama', 'tgl': 'c.tgl_spk'}


def test_page_math():
    page = Page([], total=45, page=2, per_page=10)
    assert page.pages == 5
    assert (page.first_index, page.last_index) == (11, 20)
    assert page.has_prev and page.has_next


def test_page_clamps_out_of_range():
    assert Page([], total=5, page=99, per_page=10).page == 1
    assert Page([], total=0, page=0, per_page=10).first_index == 0


def test_iter_pages_uses_ellipsis():
    page = Page([], total=200, page=10, per_page=10)
    assert list(page.iter_pages()) == [1, None, 8, 9, 10, 11, 12, None, 20]


def test_list_params_whitelists_sort_and_per_page(app):
    with app.test_request_context('/?sort=drop table&dir=sideways&per_page=999&page=abc'):
        params = ListParams(SORTABLE, default_sort='nama')
        assert params.order_by == 'c.nama ASC'
        assert params.per_page == app.config['PER_PAGE_DEFAULT']
        assert params.page == 1


def test_list_params_escapes_like(app):
    with app.test_request_context('/?q=50%_off&sort=tgl&dir=desc'):
        params = ListParams(SORTABLE, default_sort='nama')
        assert params.like == r'%50\%\_off%'
        assert params.order_by == 'c.tgl_spk DESC'
