from rest_framework import serializers
from .models import ApiToken


class ApiTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiToken
        fields = ['id', 'name', 'token', 'created_at', 'last_used', 'is_active']
        read_only_fields = ['id', 'token', 'created_at', 'last_used']


class CreateApiTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiToken
        fields = ['name']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)