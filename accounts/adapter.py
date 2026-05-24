from allauth.account.adapter import DefaultAccountAdapter
from django.utils.http import url_has_allowed_host_and_scheme

SESSION_KEY = '_next_after_login'


class AccountAdapter(DefaultAccountAdapter):
    """
    メール確認後の自動ログイン時にセッションに保存した next URL へリダイレクトする。
    通常の ?next= はメール確認フローで消えてしまうため、セッション経由で引き継ぐ。
    """

    def _pop_next(self, request):
        """セッションから next URL を取り出す（1回だけ使用）"""
        next_url = request.session.pop(SESSION_KEY, None)
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return next_url
        return None

    def get_email_verification_redirect_url(self, email_address):
        """メール確認完了後のリダイレクト先（allauth v65+）"""
        next_url = self._pop_next(self.request)
        if next_url:
            return next_url
        return super().get_email_verification_redirect_url(email_address)

    def get_login_redirect_url(self, request):
        """通常ログイン後のリダイレクト先（フォールバック）"""
        next_url = self._pop_next(request)
        if next_url:
            return next_url
        return super().get_login_redirect_url(request)
