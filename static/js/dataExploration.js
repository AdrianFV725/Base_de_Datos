// Inicializar cuando el documento se haya cargado completamente
document.addEventListener('DOMContentLoaded', function() {
    // Gestionar las keyword chips para filtrar contenido
    const keywordChips = document.querySelectorAll('.keyword-chip');
    const activeKeywords = new Set();
    
    keywordChips.forEach(chip => {
        chip.addEventListener('click', function() {
            this.classList.toggle('active');
            
            const keyword = this.textContent.trim();
            if (this.classList.contains('active')) {
                activeKeywords.add(keyword);
            } else {
                activeKeywords.delete(keyword);
            }
            
            // Aquí se podría implementar el filtrado de los gráficos basado en las palabras clave seleccionadas
            console.log('Filtrar por keywords:', Array.from(activeKeywords));
        });
    });
    
    // Gestionar el dropdown de regiones para mejorar la experiencia
    const regionSelect = document.getElementById('region-select');
    if (regionSelect) {
        // Mostrar un mensaje cuando no hay regiones disponibles
        if (regionSelect.options.length <= 1) {
            const noRegionsOption = document.createElement('option');
            noRegionsOption.text = "No hay regiones disponibles";
            noRegionsOption.disabled = true;
            regionSelect.add(noRegionsOption);
        }
        
        // Destacar el dropdown cuando se carga la página para que sea más visible
        setTimeout(() => {
            regionSelect.classList.add('highlight');
            setTimeout(() => {
                regionSelect.classList.remove('highlight');
            }, 1500);
        }, 500);
        
        // Buscar en las opciones al escribir
        regionSelect.addEventListener('keydown', function(e) {
            if (e.key.length === 1) { // Si es un carácter
                const searchTerm = e.key.toLowerCase();
                for (let i = 0; i < this.options.length; i++) {
                    const optionText = this.options[i].text.toLowerCase();
                    if (optionText.startsWith(searchTerm)) {
                        this.selectedIndex = i;
                        break;
                    }
                }
            }
        });
    }
    
    // Gestionar validación del formulario de rango de fechas
    const filterForm = document.getElementById('filter-form');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (filterForm) {
        filterForm.addEventListener('submit', function(event) {
            const startDate = new Date(startDateInput.value);
            const endDate = new Date(endDateInput.value);
            
            // Validar que la fecha de inicio sea anterior a la fecha final
            if (startDateInput.value && endDateInput.value && startDate > endDate) {
                event.preventDefault();
                alert('La fecha de inicio debe ser anterior a la fecha final');
            }
        });
    }
    
    // Gestionar botones de descarga
    const downloadButtons = document.querySelectorAll('.download-btn');
    
    downloadButtons.forEach((button, index) => {
        button.addEventListener('click', function() {
            const charts = ['timeline-chart', 'wordfreq-chart', 'geo-chart'];
            const targetChart = document.getElementById(charts[index]);
            
            if (targetChart) {
                // En una implementación real, aquí se enviaría el gráfico a una API de procesamiento
                // para generar la imagen y descargarla
                console.log(`Descargando gráfico: ${charts[index]}`);
                alert(`Se descargará el gráfico: ${charts[index].replace('-chart', '')}`);
            }
        });
    });
    
    // Gestionar vista detallada de historias
    const viewStoryButtons = document.querySelectorAll('.view-story-btn');
    
    viewStoryButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const storyCard = this.closest('.story-card');
            const storyTitle = storyCard.querySelector('h3').textContent;
            const storyAuthor = storyCard.querySelector('.story-author').textContent;
            const storyId = this.getAttribute('data-story-id');
            
            // Usar los datos precargados en lugar de hacer una llamada API
            if (storyDetailsData && storyDetailsData[storyId]) {
                const data = storyDetailsData[storyId];
                
                // Rellenar el modal con los datos obtenidos
                document.getElementById('storyModalTitle').textContent = data.title || storyTitle;
                document.getElementById('storyModalAuthor').textContent = data.author || storyAuthor;
                
                // Mostrar resumen con mejor formato
                const summaryElement = document.getElementById('storyModalSummary');
                if (data.summary && data.summary.trim() !== '') {
                    summaryElement.textContent = data.summary;
                } else {
                    summaryElement.innerHTML = '<em>No hay resumen disponible para esta historia.</em>';
                }
                
                // Información demográfica
                document.getElementById('storyModalGender').textContent = data.gender || 'No especificado';
                document.getElementById('storyModalEducation').textContent = data.education || 'No especificado';
                document.getElementById('storyModalStatus').textContent = data.marital_status || 'No especificado';
                
                // Información de viaje
                document.getElementById('storyModalCountry').textContent = data.departure_country || 'No especificado';
                document.getElementById('storyModalDate').textContent = data.departure_date || 'No especificada';
                document.getElementById('storyModalMotive').textContent = data.motive || 'No especificado';
                document.getElementById('storyModalMethod').textContent = data.travel_method || 'No especificado';
                
                // Actualizar el enlace para ver la historia completa
                document.getElementById('storyModalFullLink').href = data.full_details_url || '#';
                
                // Palabras clave
                const keywordsContainer = document.getElementById('storyModalKeywords');
                keywordsContainer.innerHTML = '';
                if (data.keywords && data.keywords.length > 0) {
                    data.keywords.forEach(keyword => {
                        const keywordBadge = document.createElement('span');
                        keywordBadge.className = 'keyword-badge';
                        keywordBadge.textContent = keyword;
                        keywordsContainer.appendChild(keywordBadge);
                    });
                } else {
                    keywordsContainer.innerHTML = '<p class="text-muted"><em>No hay palabras clave disponibles para esta historia.</em></p>';
                }
                
                // Mostrar el modal
                const storyModal = new bootstrap.Modal(document.getElementById('storyDetailsModal'));
                storyModal.show();
            } else {
                console.error(`No se encontraron detalles para la historia con ID: ${storyId}`);
                alert('Error: No se pudieron cargar los detalles de esta historia.');
            }
        });
    });
    
    // Funcionalidad del buscador de historias
    const searchBox = document.querySelector('.search-box input');
    const searchButton = document.querySelector('.search-box button');
    const storyCards = document.querySelectorAll('.story-card');
    
    function performSearch() {
        const searchTerm = searchBox.value.toLowerCase().trim();
        
        if (!searchTerm) {
            // Si el campo de búsqueda está vacío, mostrar todas las historias
            storyCards.forEach(card => {
                card.style.display = 'flex';
            });
            return;
        }
        
        storyCards.forEach(card => {
            const title = card.querySelector('h3').textContent.toLowerCase();
            const author = card.querySelector('.story-author').textContent.toLowerCase();
            
            if (title.includes(searchTerm) || author.includes(searchTerm)) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    if (searchButton && searchBox) {
        searchButton.addEventListener('click', function(event) {
            event.preventDefault();
            performSearch();
        });
        
        searchBox.addEventListener('keyup', function(event) {
            if (event.key === 'Enter') {
                performSearch();
            }
        });
    }
});

// Configurar gráficos de Highcharts
function setupCharts(years, counts, wfWords, wfCnts, geoC, geoCnt) {
    // 1) Gráfico de tendencia (timeline)
    Highcharts.chart('timeline-chart', {
        chart: { 
            type: 'line',
            backgroundColor: 'transparent'
        },
        title: { 
            text: 'Stories per Year',
            style: {
                color: '#4A4A4A',
                fontWeight: 'bold'
            }
        },
        xAxis: { 
            categories: years,
            lineColor: '#ddd',
            labels: {
                style: {
                    color: '#666'
                }
            }
        },
        yAxis: { 
            title: { 
                text: 'Number of Stories',
                style: {
                    color: '#666'
                }
            },
            gridLineColor: '#eee'
        },
        plotOptions: {
            line: {
                color: '#A75D3C',
                lineWidth: 3,
                marker: {
                    fillColor: '#A75D3C',
                    lineColor: '#fff',
                    lineWidth: 2
                }
            }
        },
        series: [{ 
            name: 'Stories', 
            data: counts 
        }]
    });
    
    // 2) Gráfico de frecuencia de palabras (barras)
    Highcharts.chart('wordfreq-chart', {
        chart: { 
            type: 'column',
            backgroundColor: 'transparent'
        },
        title: { 
            text: 'Keywords',
            style: {
                color: '#4A4A4A',
                fontWeight: 'bold'
            }
        },
        xAxis: { 
            categories: wfWords, 
            crosshair: true,
            labels: {
                style: {
                    color: '#666'
                }
            }
        },
        yAxis: { 
            title: { 
                text: 'Total Frequency',
                style: {
                    color: '#666'
                }
            },
            gridLineColor: '#eee'
        },
        plotOptions: {
            column: {
                borderRadius: 5,
                colorByPoint: true,
                colors: [
                    '#A75D3C', '#C18F34', '#66705C', '#D9A282', '#B9C09A',
                    '#8F4A30', '#D5B96D', '#4F5647', '#E6C2AF', '#CCD9B4'
                ]
            }
        },
        series: [{ 
            name: 'Frequency', 
            data: wfCnts,
            showInLegend: false
        }]
    });
    
    // 3) Gráfico de distribución geográfica (pie)
    Highcharts.chart('geo-chart', {
        chart: { 
            type: 'pie',
            backgroundColor: 'transparent'
        },
        title: { 
            text: 'Countries of Origin',
            style: {
                color: '#4A4A4A',
                fontWeight: 'bold'
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                borderRadius: 3,
                colors: [
                    '#A75D3C', '#C18F34', '#66705C', '#D9A282', '#B9C09A',
                    '#8F4A30', '#D5B96D', '#4F5647', '#E6C2AF', '#CCD9B4'
                ],
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.percentage:.1f}%',
                    style: {
                        color: '#666'
                    }
                }
            }
        },
        series: [{
            name: 'Count',
            colorByPoint: true,
            data: geoC.map((c,i) => ({ name: c, y: geoCnt[i] }))
        }]
    });
} 