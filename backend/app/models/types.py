from sqlalchemy import BigInteger, Integer

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")
