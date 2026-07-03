from app.models.category import Category
from app.models.product import Product, ProductVariant


def test_list_products_supports_filters_and_search(client, db_session, auth_headers):
    category_a = Category(name="Camisetas")
    category_b = Category(name="Calcas")
    db_session.add_all([category_a, category_b])
    db_session.flush()

    product_a = Product(name="Camiseta Basic Azul", category_id=category_a.id)
    product_b = Product(name="Calca Slim Preta", category_id=category_b.id)
    product_c = Product(name="Camiseta Premium Branca", category_id=category_a.id, is_active=False)
    db_session.add_all([product_a, product_b, product_c])
    db_session.commit()

    headers = auth_headers("manager@catalogo.com", "secret123", "manager")

    response = client.get(
        f"/products/?category_id={category_a.id}&q=Camiseta&is_active=true",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Camiseta Basic Azul"


def test_list_variants_supports_lookup_by_sku_and_barcode(client, db_session, auth_headers):
    product = Product(name="Tenis Corrida")
    db_session.add(product)
    db_session.flush()

    variant_a = ProductVariant(
        product_id=product.id,
        sku="TENIS-001",
        barcode="7890001112223",
        cost_price=100,
        sale_price=150,
    )
    variant_b = ProductVariant(
        product_id=product.id,
        sku="TENIS-002",
        barcode="7890001112224",
        cost_price=105,
        sale_price=155,
    )
    db_session.add_all([variant_a, variant_b])
    db_session.commit()

    headers = auth_headers("operator@catalogo.com", "secret123", "operator")

    sku_response = client.get("/variants/?sku=TENIS-002", headers=headers)
    assert sku_response.status_code == 200
    sku_body = sku_response.json()
    assert len(sku_body) == 1
    assert sku_body[0]["barcode"] == "7890001112224"

    barcode_response = client.get("/variants/?barcode=7890001112223", headers=headers)
    assert barcode_response.status_code == 200
    barcode_body = barcode_response.json()
    assert len(barcode_body) == 1
    assert barcode_body[0]["sku"] == "TENIS-001"


def test_product_can_be_updated_and_deactivated(client, db_session, auth_headers):
    product = Product(name="Jaqueta Corta Vento", brand="Marca A", is_active=True)
    db_session.add(product)
    db_session.commit()

    headers = auth_headers("manager@catalogo.com", "secret123", "manager")

    response = client.patch(
        f"/products/{product.id}",
        headers=headers,
        json={
            "name": "Jaqueta Corta Vento Pro",
            "brand": "Marca B",
            "is_active": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Jaqueta Corta Vento Pro"
    assert body["brand"] == "Marca B"
    assert body["is_active"] is False


def test_variant_can_be_updated(client, db_session, auth_headers):
    product = Product(name="Mochila Trek")
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="MOCHILA-001",
        barcode="7891234567890",
        cost_price=80,
        sale_price=120,
    )
    db_session.add(variant)
    db_session.commit()

    headers = auth_headers("manager@catalogo.com", "secret123", "manager")

    response = client.patch(
        f"/variants/{variant.id}",
        headers=headers,
        json={
            "sku": "MOCHILA-001-A",
            "sale_price": "135.00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "MOCHILA-001-A"
    assert body["sale_price"] == "135.00"


def test_product_and_variant_can_be_fetched_by_id(client, db_session, auth_headers):
    product = Product(name="Bone Aba Curva", brand="Marca X")
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="BONE-001",
        barcode="7895554443332",
        cost_price=20,
        sale_price=45,
    )
    db_session.add(variant)
    db_session.commit()

    headers = auth_headers("operator@catalogo.com", "secret123", "operator")

    product_response = client.get(f"/products/{product.id}", headers=headers)
    assert product_response.status_code == 200
    assert product_response.json()["name"] == "Bone Aba Curva"

    variant_response = client.get(f"/variants/{variant.id}", headers=headers)
    assert variant_response.status_code == 200
    assert variant_response.json()["sku"] == "BONE-001"


def test_product_and_variant_return_404_when_not_found(client, auth_headers):
    headers = auth_headers("operator@catalogo.com", "secret123", "operator")
    missing_id = "00000000-0000-0000-0000-000000000001"

    product_response = client.get(f"/products/{missing_id}", headers=headers)
    variant_response = client.get(f"/variants/{missing_id}", headers=headers)

    assert product_response.status_code == 404
    assert variant_response.status_code == 404
