<!--

erDiagram
orders {
 BIGINT id PK
   VARCHAR(20) cancelled_by 
   TIMESTAMP order_date 
   BIGINT restaurant_id 
   VARCHAR(20) status 
   DOUBLE_PRECISION total_price 
   BIGINT user_id 
}
restaurants {
 BIGINT id PK
   VARCHAR(1000) announcement_text 
   VARCHAR(20) delivery_status 
   VARCHAR(15) gstIN 
   VARCHAR(255) image_url 
   VARCHAR(20) kitchen_status 
   VARCHAR(100) location 
   VARCHAR(20) mobile_number 
   VARCHAR(100) name 
   VARCHAR(20) operating_status 
   VARCHAR(128) password 
   VARCHAR(100) support_email 
   UUID table_id 
}
users {
 BIGINT id PK
   VARCHAR(100) current_location 
   VARCHAR(100) email 
   VARCHAR(255) image_url 
   BOOLEAN is_hotel_owner 
   VARCHAR(100) location 
   VARCHAR(128) password 
   UUID table_id 
   VARCHAR(50) username 
}
cuisines {
 BIGINT id PK
   VARCHAR(20) category 
   VARCHAR(100) cuisine_name 
   BOOLEAN is_active 
   DOUBLE_PRECISION price_full 
   DOUBLE_PRECISION price_half 
   BIGINT restaurant_id 
   BIGINT restaurant_specific_cuisine_id 
}
feedbacks {
 BIGINT id PK
   VARCHAR(500) comments 
   BIGINT order_id 
   DOUBLE_PRECISION rating 
   BIGINT restaurant_id 
   BIGINT user_id 
}
alembic_version {
 VARCHAR(32) version_num PK
}
order_items {
 BIGINT id PK
   BIGINT cuisine_id 
   BIGINT order_id 
   DOUBLE_PRECISION price_at_purchase 
   INTEGER quantity 
   VARCHAR(10) size 
}
restaurants 1--0+ orders : has
users 1--0+ orders : has
restaurants 1--0+ cuisines : has
restaurants 1--0+ feedbacks : has
orders 1--0+ feedbacks : has
users 1--0+ feedbacks : has
cuisines 1--0+ order_items : has
orders 1--0+ order_items : has

-->
![](https://mermaid.ink/img/ZXJEaWFncmFtCm9yZGVycyB7CiBCSUdJTlQgaWQgUEsKICAgVkFSQ0hBUigyMCkgY2FuY2VsbGVkX2J5IAogICBUSU1FU1RBTVAgb3JkZXJfZGF0ZSAKICAgQklHSU5UIHJlc3RhdXJhbnRfaWQgCiAgIFZBUkNIQVIoMjApIHN0YXR1cyAKICAgRE9VQkxFX1BSRUNJU0lPTiB0b3RhbF9wcmljZSAKICAgQklHSU5UIHVzZXJfaWQgCn0KcmVzdGF1cmFudHMgewogQklHSU5UIGlkIFBLCiAgIFZBUkNIQVIoMTAwMCkgYW5ub3VuY2VtZW50X3RleHQgCiAgIFZBUkNIQVIoMjApIGRlbGl2ZXJ5X3N0YXR1cyAKICAgVkFSQ0hBUigxNSkgZ3N0SU4gCiAgIFZBUkNIQVIoMjU1KSBpbWFnZV91cmwgCiAgIFZBUkNIQVIoMjApIGtpdGNoZW5fc3RhdHVzIAogICBWQVJDSEFSKDEwMCkgbG9jYXRpb24gCiAgIFZBUkNIQVIoMjApIG1vYmlsZV9udW1iZXIgCiAgIFZBUkNIQVIoMTAwKSBuYW1lIAogICBWQVJDSEFSKDIwKSBvcGVyYXRpbmdfc3RhdHVzIAogICBWQVJDSEFSKDEyOCkgcGFzc3dvcmQgCiAgIFZBUkNIQVIoMTAwKSBzdXBwb3J0X2VtYWlsIAogICBVVUlEIHRhYmxlX2lkIAp9CnVzZXJzIHsKIEJJR0lOVCBpZCBQSwogICBWQVJDSEFSKDEwMCkgY3VycmVudF9sb2NhdGlvbiAKICAgVkFSQ0hBUigxMDApIGVtYWlsIAogICBWQVJDSEFSKDI1NSkgaW1hZ2VfdXJsIAogICBCT09MRUFOIGlzX2hvdGVsX293bmVyIAogICBWQVJDSEFSKDEwMCkgbG9jYXRpb24gCiAgIFZBUkNIQVIoMTI4KSBwYXNzd29yZCAKICAgVVVJRCB0YWJsZV9pZCAKICAgVkFSQ0hBUig1MCkgdXNlcm5hbWUgCn0KY3Vpc2luZXMgewogQklHSU5UIGlkIFBLCiAgIFZBUkNIQVIoMjApIGNhdGVnb3J5IAogICBWQVJDSEFSKDEwMCkgY3Vpc2luZV9uYW1lIAogICBCT09MRUFOIGlzX2FjdGl2ZSAKICAgRE9VQkxFX1BSRUNJU0lPTiBwcmljZV9mdWxsIAogICBET1VCTEVfUFJFQ0lTSU9OIHByaWNlX2hhbGYgCiAgIEJJR0lOVCByZXN0YXVyYW50X2lkIAogICBCSUdJTlQgcmVzdGF1cmFudF9zcGVjaWZpY19jdWlzaW5lX2lkIAp9CmZlZWRiYWNrcyB7CiBCSUdJTlQgaWQgUEsKICAgVkFSQ0hBUig1MDApIGNvbW1lbnRzIAogICBCSUdJTlQgb3JkZXJfaWQgCiAgIERPVUJMRV9QUkVDSVNJT04gcmF0aW5nIAogICBCSUdJTlQgcmVzdGF1cmFudF9pZCAKICAgQklHSU5UIHVzZXJfaWQgCn0KYWxlbWJpY192ZXJzaW9uIHsKIFZBUkNIQVIoMzIpIHZlcnNpb25fbnVtIFBLCn0Kb3JkZXJfaXRlbXMgewogQklHSU5UIGlkIFBLCiAgIEJJR0lOVCBjdWlzaW5lX2lkIAogICBCSUdJTlQgb3JkZXJfaWQgCiAgIERPVUJMRV9QUkVDSVNJT04gcHJpY2VfYXRfcHVyY2hhc2UgCiAgIElOVEVHRVIgcXVhbnRpdHkgCiAgIFZBUkNIQVIoMTApIHNpemUgCn0KcmVzdGF1cmFudHMgMS0tMCsgb3JkZXJzIDogaGFzCnVzZXJzIDEtLTArIG9yZGVycyA6IGhhcwpyZXN0YXVyYW50cyAxLS0wKyBjdWlzaW5lcyA6IGhhcwpyZXN0YXVyYW50cyAxLS0wKyBmZWVkYmFja3MgOiBoYXMKb3JkZXJzIDEtLTArIGZlZWRiYWNrcyA6IGhhcwp1c2VycyAxLS0wKyBmZWVkYmFja3MgOiBoYXMKY3Vpc2luZXMgMS0tMCsgb3JkZXJfaXRlbXMgOiBoYXMKb3JkZXJzIDEtLTArIG9yZGVyX2l0ZW1zIDogaGFz)
