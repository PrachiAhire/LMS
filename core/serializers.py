from rest_framework import serializers
from .models import User, Course, Module, Enrollment

class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name', required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        name = validated_data.pop('first_name', '')
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=name,
            role=validated_data.get('role', 'student'),
            password=validated_data['password']
        )
        return user

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'title', 'order_index']

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    instructor_name = serializers.CharField(source='instructor.first_name', read_only=True)
    instructor_email = serializers.CharField(source='instructor.email', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'instructor', 'instructor_name', 'instructor_email', 'modules', 'created_at']
        read_only_fields = ['instructor', 'created_at']
        
class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_id = serializers.IntegerField(source='course.id', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course_id', 'course_title', 'enrolled_at']