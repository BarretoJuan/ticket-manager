"""SAT sync DTOs: start-sync response, history status and paginated list."""

from rest_framework import serializers


class SatHistoryResponseDTO(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)
    user_id = serializers.UUIDField(allow_null=True, required=False)
    file_hash = serializers.CharField(allow_null=True, required=False)
    processing_time = serializers.FloatField(allow_null=True, required=False)
    record_number = serializers.IntegerField()
    omitted_number = serializers.IntegerField()


class SatSyncStartedDTO(serializers.Serializer):
    history_id = serializers.UUIDField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    force = serializers.BooleanField()


class SatSyncSkipDTO(serializers.Serializer):
    status = serializers.CharField()
    reason = serializers.CharField()
    next_allowed_at = serializers.DateTimeField(allow_null=True, required=False)
    last_sync = SatHistoryResponseDTO(required=False, allow_null=True)


class SatHistoryQueryDTO(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)


class SatHistoryListResponseDTO(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True, required=False)
    previous = serializers.CharField(allow_null=True, required=False)
    results = SatHistoryResponseDTO(many=True)
