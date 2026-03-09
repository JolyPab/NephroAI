class User {
  final int id;
  final String email;
  final String? name;
  final bool isDoctor;
  final bool isVerified;

  User({
    required this.id,
    required this.email,
    this.name,
    this.isDoctor = false,
    this.isVerified = false,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: json['id'] as int,
        email: json['email'] as String,
        name: json['name'] as String?,
        isDoctor: json['is_doctor'] as bool? ?? false,
        isVerified: json['is_verified'] as bool? ?? false,
      );

  String get displayName => name?.isNotEmpty == true ? name! : email;
}
