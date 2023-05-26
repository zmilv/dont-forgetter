from django.contrib import admin
from .models import Event, Note


class NoteAdmin(admin.ModelAdmin):
    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(Event)
admin.site.register(Note, NoteAdmin)
