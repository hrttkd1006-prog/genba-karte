from django.contrib import admin
from django.utils.html import format_html
from .models import Review, Objection


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'overall_rating', 'ai_judgment', 'status', 'created_at', 'action_buttons']
    list_filter = ['status', 'ai_judgment', 'employment_type']
    search_fields = ['hospital__name', 'good_points', 'concerns']
    readonly_fields = ['ai_judgment', 'ai_reason', 'ip_address', 'created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 30

    # グレー判定のみ絞り込むフィルター
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.GET.get('pending_only'):
            return qs.filter(status='pending', ai_judgment='gray')
        return qs

    def action_buttons(self, obj):
        if obj.status == 'pending':
            approve_url = f'/admin/reviews/review/{obj.pk}/approve/'
            reject_url = f'/admin/reviews/review/{obj.pk}/reject/'
            return format_html(
                '<a class="button" href="{}">承認</a> '
                '<a class="button" style="color:red" href="{}">却下</a>',
                approve_url, reject_url
            )
        return obj.get_status_display()
    action_buttons.short_description = '操作'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('<int:pk>/approve/', self.admin_site.admin_view(self.approve_review), name='review_approve'),
            path('<int:pk>/reject/', self.admin_site.admin_view(self.reject_review), name='review_reject'),
        ]
        return custom + urls

    def approve_review(self, request, pk):
        from django.shortcuts import redirect
        Review.objects.filter(pk=pk).update(status='approved')
        self.message_user(request, 'レビューを承認しました。')
        return redirect('admin:reviews_review_changelist')

    def reject_review(self, request, pk):
        from django.shortcuts import redirect
        Review.objects.filter(pk=pk).update(status='rejected')
        self.message_user(request, 'レビューを却下しました。')
        return redirect('admin:reviews_review_changelist')


@admin.register(Objection)
class ObjectionAdmin(admin.ModelAdmin):
    list_display = ['review', 'hospital_name', 'status', 'reply_deadline', 'created_at']
    list_filter = ['status']
    readonly_fields = ['created_at', 'reply_deadline']
