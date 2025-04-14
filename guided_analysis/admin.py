# guided_analysis/admin.py
from django.contrib import admin
from .models import GuidingQuestion, UserResponse

@admin.register(GuidingQuestion)
class GuidingQuestionAdmin(admin.ModelAdmin):
    list_display = ('axis_key', 'order', 'question_text_short', 'response_type', 'is_required')
    list_filter = ('axis_key', 'response_type', 'is_required')
    search_fields = ('question_text',)
    list_editable = ('order', 'is_required') # Permet modification rapide

    def question_text_short(self, obj):
        return obj.question_text[:80] + '...' if len(obj.question_text) > 80 else obj.question_text
    question_text_short.short_description = 'Texte de la Question (Tronqué)'

@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ('scenario_request_id_link', 'question_link', 'answer_summary', 'created_at')
    list_filter = ('scenario_request__user', 'question__axis_key') # Filtrer par utilisateur via la requête
    search_fields = ('answer_text', 'scenario_request__user__email', 'question__question_text')
    raw_id_fields = ('scenario_request', 'question') # Pour recherche facile si beaucoup de données

    def scenario_request_id_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:analysis_scenariorequest_change", args=[obj.scenario_request.id])
        return format_html('<a href="{}">Demande #{}</a>', link, obj.scenario_request.id)
    scenario_request_id_link.short_description = 'Demande Analyse'

    def question_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:guided_analysis_guidingquestion_change", args=[obj.question.id])
        return format_html('<a href="{}">Q{} ({})</a>', link, obj.question.id, obj.question.axis_key)
    question_link.short_description = 'Question Guidée'

    def answer_summary(self, obj):
         return obj.answer_text[:100] + '...' if obj.answer_text and len(obj.answer_text) > 100 else obj.answer_text
    answer_summary.short_description = 'Réponse (Tronquée)'