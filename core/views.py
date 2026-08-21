from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, Course, Module, Enrollment, Role
from .serializers import UserSerializer, CourseSerializer, ModuleSerializer, EnrollmentSerializer
from rest_framework_simplejwt.tokens import RefreshToken
import jwt
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

def index(request):
    """Serves the Single Page UI template."""
    return render(request, 'index.html')

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

import jwt
from django.conf import settings

class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            return Response({"detail": "No authorization header"}, status=status.HTTP_401_UNAUTHORIZED)
        
        token = auth_header.replace('Bearer', '').strip()
        
        try:
            # Decode the token using Django's secret key
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get('user_id')
            user = User.objects.filter(id=user_id).first()
            
            if not user:
                return Response({"detail": "User not found"}, status=status.HTTP_401_UNAUTHORIZED)
                
            return Response({
                "id": user.id,
                "name": user.first_name or user.email.split('@')[0],
                "email": user.email,
                "role": user.role
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"detail": f"Token validation error: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)

class CourseListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        courses = Course.objects.all().order_by('-created_at')
        serializer = CourseSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer', '').strip()
        user = None

        if token:
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user = User.objects.filter(id=payload.get('user_id')).first()
            except Exception as e:
                return Response({"detail": f"Invalid token: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        title = request.data.get('title')
        description = request.data.get('description', '')

        if not title or not description:
            return Response({"detail": "Title and description are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Create and link course to logged in user
        course = Course.objects.create(
            title=title,
            description=description,
            instructor=user
        )
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def perform_destroy(self, instance):
        if self.request.user != instance.teacher and self.request.user.role != 'admin':
            raise permissions.PermissionDenied("You cannot delete this course.")
        instance.delete()

class AddModuleView(generics.CreateAPIView):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        course = Course.objects.get(pk=self.kwargs['course_id'])
        if self.request.user != course.teacher and self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Not authorized to add modules to this course.")
        serializer.save(course=course)

class EnrollCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = Course.objects.get(pk=course_id)
        enrollment, created = Enrollment.objects.get_or_create(student=request.user, course=course)
        if not created:
            return Response({"detail": "Already enrolled in this course"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Enrolled successfully"})

class UnenrollCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, course_id):
        Enrollment.objects.filter(student=request.user, course_id=course_id).delete()
        return Response({"message": "Unenrolled successfully"})

class MyEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or request.data.get('username') or '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response({"detail": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            user = User.objects.filter(username__iexact=email).first()

        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            return Response({
                "access": access_token,
                "access_token": access_token,
                "token_type": "bearer",
                "role": user.role
            }, status=status.HTTP_200_OK)

        return Response({"detail": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)
# Create your views here.
