from django.contrib import admin

# Register your models here.

# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Course, Module, Enrollment
from django.contrib import admin
from .models import ModuleProgress
from .models import Quiz, Question, Choice, QuizSubmission

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Displays these columns in the user list view
    list_display = ('email', 'username', 'role', 'is_staff', 'is_active')
    
    # Allows filtering users by role and status in the right sidebar
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    
    # Configuration for user detail forms (groups fields logically)
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Profile Fields', {'fields': ('role',)}),
    )
    
    # Configuration for creating a new user via admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Profile Fields', {'fields': ('role',)}),
    )
    
    ordering = ('email',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'created_at')
    list_filter = ('instructor', 'created_at')
    search_fields = ('title', 'description')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'content')
    ordering = ('course', 'order')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrolled_at')
    list_filter = ('course', 'enrolled_at')
    search_fields = ('student__email', 'course__title')
9

@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'completed', 'completed_at')
    list_filter = ('completed', 'completed_at')

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]

admin.site.register(Quiz)
admin.site.register(Question, QuestionAdmin)
admin.site.register(QuizSubmission)