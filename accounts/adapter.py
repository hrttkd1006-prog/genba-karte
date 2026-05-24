from allauth.account.adapter import DefaultAccountAdapter
from django.utils.http import url_has_allowed_host_and_scheme


class AccountAdapter(DefaultAccountAdapter):
    """
    メール確認後の自動ログイン時にセッションに保存した next URL へリダイレクトする。
    通常の ?next= はメール確認フローで消えてしまうため、セッション経由で引き継ぐ。
    """

    def get_login_redirect_url(self, request):
        next_url = request.session.pop('_next_after_login', None)
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return next_url
        return super().get_login_redirect_url(request)
