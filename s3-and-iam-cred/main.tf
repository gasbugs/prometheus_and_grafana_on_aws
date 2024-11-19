# 랜덤한 S3 버킷 이름을 위한 random_id 리소스 생성
resource "random_id" "s3_suffix" {
  byte_length = 4
}

# S3 버킷 생성
resource "aws_s3_bucket" "random_bucket" {
  bucket = "my-thanos-bucket-${random_id.s3_suffix.hex}"

  tags = {
    Name        = "Thanos S3 Bucket"
    Environment = "Dev"
  }

  force_destroy = true
}

# IAM 유저 생성
resource "aws_iam_user" "s3_user" {
  name = "s3-user"
}

# IAM 정책 생성 (S3 버킷에 대한 전체 액세스 권한)
resource "aws_iam_policy" "s3_policy" {
  name        = "S3FullAccessPolicy"
  description = "IAM policy to allow full access to the S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = ["s3:*"],
        Effect = "Allow",
        Resource = [
          "${aws_s3_bucket.random_bucket.arn}",
          "${aws_s3_bucket.random_bucket.arn}/*"
        ]
      }
    ]
  })
}

# IAM 유저에 정책 연결
resource "aws_iam_user_policy_attachment" "attach_policy" {
  user       = aws_iam_user.s3_user.name
  policy_arn = aws_iam_policy.s3_policy.arn
}

# Access Key 및 Secret Key 생성
resource "aws_iam_access_key" "user_access_key" {
  user = aws_iam_user.s3_user.name

  # 출력하여 나중에 사용할 수 있도록 함
  depends_on = [aws_iam_user_policy_attachment.attach_policy]
}

# S3 엔드포인트 및 리전 정보 출력 (YAML 파일로 전달)
resource "local_file" "thanos_values_sample_yaml" {
  content = templatefile("${path.module}/thanos-values-sample.yaml.tpl", {
    bucket     = aws_s3_bucket.random_bucket.bucket,
    region     = aws_s3_bucket.random_bucket.region,
    access_key = aws_iam_access_key.user_access_key.id,
    secret_key = aws_iam_access_key.user_access_key.secret
  })

  filename = "${path.module}/thanos-values-sample.yaml"
}

# S3 엔드포인트 및 리전 정보 출력 (YAML 파일로 전달)
resource "local_file" "kube_prom_vaules_with_thanos_file" {
  content = templatefile("${path.module}/kube-prom-vaules-with-thanos.yaml.tpl", {
    bucket     = aws_s3_bucket.random_bucket.bucket,
    region     = aws_s3_bucket.random_bucket.region,
    access_key = aws_iam_access_key.user_access_key.id,
    secret_key = aws_iam_access_key.user_access_key.secret
  })

  filename = "${path.module}/kube-prom-vaules-with-thanos.yaml"
}


# 출력 값 설정 (Access Key와 Secret Key)
output "access_key" {
  value     = aws_iam_access_key.user_access_key.id
  sensitive = true
}

output "secret_key" {
  value     = aws_iam_access_key.user_access_key.secret
  sensitive = true
}
