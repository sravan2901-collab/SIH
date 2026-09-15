// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'upload_queue.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class PendingUploadAdapter extends TypeAdapter<PendingUpload> {
  @override
  final int typeId = 0;

  @override
  PendingUpload read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return PendingUpload()
      ..localId = fields[0] as String
      ..productId = fields[1] as String
      ..imagePath = fields[2] as String
      ..imageContentType = fields[3] as String
      ..capturedAt = fields[4] as DateTime
      ..remoteScanId = fields[5] as String?;
  }

  @override
  void write(BinaryWriter writer, PendingUpload obj) {
    writer
      ..writeByte(6)
      ..writeByte(0)
      ..write(obj.localId)
      ..writeByte(1)
      ..write(obj.productId)
      ..writeByte(2)
      ..write(obj.imagePath)
      ..writeByte(3)
      ..write(obj.imageContentType)
      ..writeByte(4)
      ..write(obj.capturedAt)
      ..writeByte(5)
      ..write(obj.remoteScanId);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PendingUploadAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}
