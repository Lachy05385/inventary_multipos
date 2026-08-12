// static/js/carousel.js

async function loadCarouselProducts() {
    try {
        // Obtener productos (los 10 primeros, sin autenticación)
        const products = await apiRequest('/warehouse/products?limit=10', 'GET');
        const carouselInner = document.getElementById('carouselInner');
        carouselInner.innerHTML = '';

        if (!products || products.length === 0) {
            carouselInner.innerHTML = '<div class="text-center">No hay productos disponibles.</div>';
            return;
        }

        // Agrupar de a 3 productos por slide
        const itemsPerSlide = 3;
        let slideIndex = 0;

        for (let i = 0; i < products.length; i += itemsPerSlide) {
            const slideItems = products.slice(i, i + itemsPerSlide);
            const isActive = i === 0 ? 'active' : '';

            const slideDiv = document.createElement('div');
            slideDiv.className = `carousel-item ${isActive}`;
            slideDiv.innerHTML = `
                <div class="row justify-content-center">
                    ${slideItems.map(product => `
                        <div class="col-md-4">
                            <div class="card">
                                <img src="${product.image_url || '/static/img/default-product.png'}" 
                                     class="card-img-top product-img" 
                                     alt="${product.name}">
                                <div class="card-body text-center">
                                    <h5 class="card-title">${product.name}</h5>
                                    <p class="card-text">$${product.price.toFixed(2)}</p>
                                    <button class="btn btn-outline-primary btn-sm">Ver más</button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            carouselInner.appendChild(slideDiv);
        }

        // Inicializar el carrusel (Bootstrap lo hace automático si tiene data-bs-ride)
        // Pero forzamos la actualización si es necesario
        const carousel = document.getElementById('productCarousel');
        if (carousel) {
            const bsCarousel = new bootstrap.Carousel(carousel, {
                interval: 3000,
                wrap: true
            });
        }
    } catch (error) {
        console.error('Error cargando productos:', error);
        document.getElementById('carouselInner').innerHTML = `
            <div class="alert alert-danger">Error al cargar los productos: ${error.message}</div>
        `;
    }
}

// Ejecutar al cargar la página
document.addEventListener('DOMContentLoaded', loadCarouselProducts);