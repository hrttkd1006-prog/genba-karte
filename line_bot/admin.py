from django.contrib import admin
from .models import LineUser, LineMessage, ConversationState, LineInquiry


@admin.register(LineUser)
class LineUserAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'line_user_id', 'is_followed', 'followed_at')
    search_fields = ('display_name', 'line_user_id')
    list_filter = ('is_followed',)
    readonly_fields = ('line_user_id', 'followed_at', 'unfollowed_at')


@admin.register(LineMessage)
class LineMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'direction', 'line_user', 'message_type', 'text_preview')
    list_filter = ('direction', 'message_type')
    search_fields = ('text', 'line_user__display_name')
    readonly_fields = ('line_user', 'direction', 'message_type', 'text', 'raw_event', 'created_at')

    def text_preview(self, obj):
        return obj.text[:50]
    text_preview.short_description = '本文'


@admin.register(ConversationState)
class ConversationStateAdmin(admin.ModelAdmin):
    list_display = ('line_user', 'flow_name', 'step', 'updated_at')
    list_filter = ('flow_name',)
    readonly_fields = ('updated_at',)


@admin.register(LineInquiry)
class LineInquiryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'line_user', 'body_preview', 'status')
    list_filter = ('status',)
    search_fields = ('body', 'subject', 'line_user__display_name')
    readonly_fields = ('line_user', 'body', 'created_at', 'updated_at')

    def body_preview(self, obj):
        return obj.body[:50]
    body_preview.short_description = '本文'
