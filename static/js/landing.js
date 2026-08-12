// landing.js
document.addEventListener('DOMContentLoaded', () => {
  const track = document.getElementById('carouselTrack');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const indicators = document.getElementById('indicators');

  let currentIndex = 0;
  let products = [];

  // ========== OBTENER PRODUCTOS ==========
  async function fetchProducts() {
    try {
      // Llamar a la API de productos (los 6 más recientes o destacados)
      const res = await fetch('/warehouse/products?limit=6&search=destacado');
      if (!res.ok) throw new Error('Error al cargar productos');
      const data = await res.json();
      // Si la API devuelve un array, lo usamos; si no, usamos datos de ejemplo
      return data.length ? data : getMockProducts();
    } catch (error) {
      console.warn('Usando productos de ejemplo:', error);
      return getMockProducts();
    }
  }

  // Datos de ejemplo (para que el carrusel se vea bonito sin backend)
  function getMockProducts() {
    return [
      { id: 1, name: 'Camisa Tropical', price: 29.99, old_price: 39.99, image: '/static/img/product1.jpg' },
      { id: 2, name: 'Pescado Fresco', price: 15.50, old_price: null, image: '/static/img/product2.jpg' },
      { id: 3, name: 'Sombrero de Yarey', price: 12.00, old_price: 18.00, image: '/static/img/product3.jpg' },
      { id: 4, name: 'Ron Isleño', price: 45.00, old_price: null, image: '/static/img/product4.jpg' },
      { id: 5, name: 'Pintura de la Isla', price: 80.00, old_price: 100.00, image: '/static/img/product5.jpg' },
      { id: 6, name: 'Café Cubano', price: 8.99, old_price: null, image: '/static/img/product6.jpg' },
    ];
  }

  // ========== RENDERIZAR CARRUSEL ==========
  function renderCarousel(items) {
    track.innerHTML = '';
    items.forEach(product => {
      const div = document.createElement('div');
      div.className = 'carousel-item';
      div.innerHTML = `
        <div class="product-card">
          <img src="${product.image || '/static/img/placeholder.jpg'}" alt="${product.name}" loading="lazy">
          <div class="info">
            <h3>${product.name}</h3>
            <div>
              <span class="price">$${product.price.toFixed(2)}</span>
              ${product.old_price ? `<span class="old-price">$${product.old_price.toFixed(2)}</span>` : ''}
            </div>
          </div>
        </div>
      `;
      track.appendChild(div);
    });

    // Actualizar indicadores
    indicators.innerHTML = '';
    const total = Math.ceil(items.length / 3); // asumiendo 3 por slide
    for (let i = 0; i < total; i++) {
      const dot = document.createElement('span');
      dot.dataset.index = i;
      if (i === 0) dot.classList.add('active');
      dot.addEventListener('click', () => goToSlide(i));
      indicators.appendChild(dot);
    }

    // Asegurar que el track tenga el ancho correcto
    updateCarousel();
  }

  // ========== FUNCIONES DEL CARRUSEL ==========
  function updateCarousel() {
    const totalItems = track.children.length;
    const itemsPerView = getItemsPerView();
    const maxIndex = Math.ceil(totalItems / itemsPerView) - 1;
    if (currentIndex > maxIndex) currentIndex = maxIndex;
    const offset = currentIndex * (100 / itemsPerView);
    track.style.transform = `translateX(-${offset}%)`;

    // Actualizar indicadores
    document.querySelectorAll('#indicators span').forEach((dot, i) => {
      dot.classList.toggle('active', i === currentIndex);
    });
  }

  function getItemsPerView() {
    if (window.innerWidth < 480) return 1;
    if (window.innerWidth < 768) return 2;
    return 3;
  }

  function goToSlide(index) {
    const totalItems = track.children.length;
    const itemsPerView = getItemsPerView();
    const maxIndex = Math.ceil(totalItems / itemsPerView) - 1;
    if (index < 0) index = maxIndex;
    if (index > maxIndex) index = 0;
    currentIndex = index;
    updateCarousel();
  }

  // Eventos de los botones
  prevBtn.addEventListener('click', () => goToSlide(currentIndex - 1));
  nextBtn.addEventListener('click', () => goToSlide(currentIndex + 1));

  // Recalcular al redimensionar
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      const itemsPerView = getItemsPerView();
      const totalItems = track.children.length;
      const maxIndex = Math.ceil(totalItems / itemsPerView) - 1;
      if (currentIndex > maxIndex) currentIndex = maxIndex;
      updateCarousel();
    }, 200);
  });

  // ========== INICIALIZAR ==========
  async function init() {
    products = await fetchProducts();
    renderCarousel(products);
  }

  init();
});