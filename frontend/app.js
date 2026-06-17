// DOM Elements
const slidersGrid = document.getElementById('sliders-grid');
const sensitivitySelect = document.getElementById('sensitivity-select');

// Calibration inputs
const selectCementType = document.getElementById('select-cement-type');
const selectAggregateShape = document.getElementById('select-aggregate-shape');
const selectWaterQuality = document.getElementById('select-water-quality');
const selectCuringMethod = document.getElementById('select-curing-method');
const selectQcLevel = document.getElementById('select-qc-level');
const selectDesignCode = document.getElementById('select-design-code');
const sliderSf = document.getElementById('slider-sf');
const valboxSf = document.getElementById('valbox-sf');
const sfSliderLabel = document.getElementById('sf-slider-label');

// Detailed Output fields
const outputDesignStrength = document.getElementById('output-design-strength');
const outputCharStrength = document.getElementById('output-char-strength');
const outputCalibratedMean = document.getElementById('output-calibrated-mean');
const outputRawMl = document.getElementById('output-raw-ml');
const outputReductionType = document.getElementById('output-reduction-type');
const gradeVal = document.getElementById('grade-val');
const wbVal = document.getElementById('wb-val');
const wbFeedbackTxt = document.getElementById('wb-feedback-txt');

// Multipliers
const multCement = document.getElementById('multiplier-cement');
const multAggregate = document.getElementById('multiplier-aggregate');
const multWater = document.getElementById('multiplier-water');
const multCuring = document.getElementById('multiplier-curing');
const multTotal = document.getElementById('multiplier-total');

// Alerts
const alertsBox = document.getElementById('alerts-box');
const alertsList = document.getElementById('alerts-list');

// Global State
let modelMetadata = null;
let currentMix = {};
let sensitivityChart = null;
const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000/api' : '/api';

const featureLabels = {
    'cement': { name: 'Cement', unit: 'kg/m³', desc: 'Primary hydraulic binder' },
    'slag': { name: 'Blast Furnace Slag', unit: 'kg/m³', desc: 'Latent hydraulic binder' },
    'ash': { name: 'Fly Ash', unit: 'kg/m³', desc: 'Pozzolanic binder' },
    'water': { name: 'Water', unit: 'kg/m³', desc: 'Chemical reactant & lubricant' },
    'superplastic': { name: 'Superplasticizer', unit: 'kg/m³', desc: 'High-range water reducer' },
    'coarseagg': { name: 'Coarse Aggregate', unit: 'kg/m³', desc: 'Gravel/Crushed stone (stone skeleton)' },
    'fineagg': { name: 'Fine Aggregate', unit: 'kg/m³', desc: 'Sand (void filler)' },
    'age': { name: 'Curing Age', unit: 'Days', desc: 'Hydration period' }
};

// Initialize App
async function init() {
    try {
        await fetchMetadata();
        buildSliders();
        initDropdowns();
        setupEventListeners();
        await updateDashboard();
    } catch (err) {
        console.error("Initialization failed:", err);
        slidersGrid.innerHTML = `<div class="slider-group-error" style="color:var(--accent-danger); padding:20px; text-align:center;">
            <i class="fa-solid fa-triangle-exclamation" style="font-size:2rem; margin-bottom:10px; display:block;"></i>
            Failed to connect to backend server. Make sure the FastAPI application is running.
        </div>`;
    }
}

// Fetch ML metadata
async function fetchMetadata() {
    const res = await fetch(`${API_BASE}/metadata`);
    if (!res.ok) throw new Error("Metadata fetch failed");
    modelMetadata = await res.json();
}

// Dynamically create mixSliders
function buildSliders() {
    slidersGrid.innerHTML = '';
    const limits = modelMetadata.feature_limits;
    const order = ['cement', 'slag', 'ash', 'water', 'superplastic', 'coarseagg', 'fineagg', 'age'];
    
    order.forEach(key => {
        if (!limits[key]) return;
        const lim = limits[key];
        const initialVal = Math.round(lim.mean * 10) / 10;
        currentMix[key] = initialVal;
        
        const info = featureLabels[key] || { name: key, unit: '', desc: '' };
        
        const sliderItem = document.createElement('div');
        sliderItem.className = 'slider-item';
        sliderItem.innerHTML = `
            <div class="slider-info">
                <div>
                    <span class="slider-label">${info.name}</span>
                    <span class="slider-unit">(${info.unit})</span>
                </div>
                <div class="slider-val-box" id="valbox-${key}">${initialVal}</div>
            </div>
            <div class="slider-input-container">
                <input type="range" class="slider-control" id="slider-${key}" 
                    min="${lim.min}" max="${lim.max}" step="${lim.step}" value="${initialVal}">
            </div>
            <div class="slider-limits">
                <span>Min: ${lim.min}</span>
                <span style="opacity: 0.6;">${info.desc}</span>
                <span>Max: ${lim.max}</span>
            </div>
        `;
        
        slidersGrid.appendChild(sliderItem);
    });
    
    // Add default calibration keys
    syncCalibrationState();
}

function initDropdowns() {
    // Dropdown change listeners
    const dropdowns = [
        selectCementType, selectAggregateShape, selectWaterQuality, 
        selectCuringMethod, selectQcLevel, selectDesignCode
    ];
    
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('change', () => {
            if (dropdown === selectDesignCode) {
                // Adjust safety factor defaults depending on selected design code
                if (selectDesignCode.value === 'aci_318') {
                    sfSliderLabel.innerText = "Safety Divisor (1/φ)";
                    sliderSf.value = 1.54; // default phi = 0.65 -> sf = 1.54
                    valboxSf.innerText = "1.54";
                } else {
                    sfSliderLabel.innerText = "Material Safety Factor (γ_c)";
                    sliderSf.value = 1.50; // default gamma_c = 1.50
                    valboxSf.innerText = "1.50";
                }
            }
            syncCalibrationState();
            updateDashboard();
        });
    });

    // Sensitivity Select listener
    sensitivitySelect.addEventListener('change', () => {
        updateSensitivityChart();
    });

    // Safety Factor Slider listener
    sliderSf.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value).toFixed(2);
        valboxSf.innerText = val;
        currentMix['safety_factor'] = parseFloat(val);
        debounceUpdate();
    });
}

function syncCalibrationState() {
    currentMix['cement_type'] = selectCementType.value;
    currentMix['aggregate_shape'] = selectAggregateShape.value;
    currentMix['water_quality'] = selectWaterQuality.value;
    currentMix['curing_method'] = selectCuringMethod.value;
    currentMix['quality_control'] = selectQcLevel.value;
    currentMix['design_code'] = selectDesignCode.value;
    currentMix['safety_factor'] = parseFloat(sliderSf.value);
}

function setupEventListeners() {
    const limits = modelMetadata.feature_limits;
    Object.keys(limits).forEach(key => {
        const slider = document.getElementById(`slider-${key}`);
        const valBox = document.getElementById(`valbox-${key}`);
        
        slider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            valBox.innerText = val;
            currentMix[key] = val;
            debounceUpdate();
        });
    });
}

let debounceTimer;
function debounceUpdate() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        updateDashboard();
    }, 150);
}

// Update outputs from API
async function updateDashboard() {
    try {
        syncCalibrationState();
        
        const res = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentMix)
        });
        
        if (!res.ok) throw new Error("Prediction API error");
        
        const data = await res.json();
        
        // 1. Update Strengths
        outputDesignStrength.innerText = data.design_strength.toFixed(1);
        outputCharStrength.innerText = data.characteristic_strength.toFixed(1);
        outputCalibratedMean.innerText = data.calibrated_mean.toFixed(1);
        outputRawMl.innerText = data.raw_prediction.toFixed(1);
        outputReductionType.innerText = data.reduction_label;
        
        // Dynamic design strength coloring
        if (data.design_strength >= 30) {
            outputDesignStrength.style.color = 'var(--accent-green)';
            outputDesignStrength.style.textShadow = '0 0 15px rgba(16, 185, 129, 0.3)';
        } else if (data.design_strength < 15) {
            outputDesignStrength.style.color = 'var(--accent-danger)';
            outputDesignStrength.style.textShadow = '0 0 15px rgba(239, 68, 68, 0.3)';
        } else {
            outputDesignStrength.style.color = 'var(--accent-cyan)';
            outputDesignStrength.style.textShadow = '0 0 15px rgba(6, 182, 212, 0.3)';
        }
        
        // 2. Badges and general mix stats
        gradeVal.innerText = data.grade;
        wbVal.innerText = data.wb_ratio.toFixed(2);
        wbFeedbackTxt.innerText = data.wb_feedback;
        
        // W/B feedback border color
        if (data.wb_ratio > 0.60 || data.wb_ratio < 0.30) {
            wbFeedbackTxt.style.borderLeftColor = 'var(--accent-danger)';
        } else if (data.wb_ratio > 0.50 || data.wb_ratio < 0.40) {
            wbFeedbackTxt.style.borderLeftColor = 'var(--accent-warning)';
        } else {
            wbFeedbackTxt.style.borderLeftColor = 'var(--accent-green)';
        }

        // 3. Update Calibration factors
        multCement.innerText = data.factors.cement.toFixed(2);
        multAggregate.innerText = data.factors.aggregate.toFixed(2);
        multWater.innerText = data.factors.water.toFixed(2);
        multCuring.innerText = data.factors.curing.toFixed(2);
        multTotal.innerText = data.factors.total.toFixed(2);
        
        if (data.factors.total < 1.0) {
            multTotal.parentElement.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
            multTotal.parentElement.style.borderColor = 'rgba(239, 68, 68, 0.2)';
            multTotal.style.color = 'var(--accent-danger)';
        } else {
            multTotal.parentElement.style.backgroundColor = 'rgba(6, 182, 212, 0.1)';
            multTotal.parentElement.style.borderColor = 'rgba(6, 182, 212, 0.2)';
            multTotal.style.color = 'var(--accent-cyan)';
        }

        // 4. Update Alerts List
        if (data.alerts && data.alerts.length > 0) {
            alertsBox.style.display = 'block';
            alertsList.innerHTML = '';
            data.alerts.forEach(alertText => {
                const li = document.createElement('li');
                li.innerText = alertText;
                alertsList.appendChild(li);
            });
        } else {
            alertsBox.style.display = 'none';
        }
        
        // 5. Update chart
        await updateSensitivityChart();
        
    } catch (err) {
        console.error("Dashboard update failed:", err);
    }
}

// Update sensitivity chart
async function updateSensitivityChart() {
    const target = sensitivitySelect.value;
    
    try {
        const res = await fetch(`${API_BASE}/sensitivity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mix: currentMix,
                target_feature: target
            })
        });
        
        if (!res.ok) throw new Error("Sensitivity API error");
        const result = await res.json();
        
        const labels = result.data.map(item => item.value);
        const strengths = result.data.map(item => item.strength);
        
        const labelInfo = featureLabels[target] || { name: target, unit: '' };
        
        if (sensitivityChart) {
            // Update existing chart
            sensitivityChart.data.labels = labels;
            sensitivityChart.data.datasets[0].label = `Design Strength vs ${labelInfo.name} (${labelInfo.unit})`;
            sensitivityChart.data.datasets[0].data = strengths;
            
            // Add a vertical line annotation for current mix value
            const currentVal = currentMix[target];
            sensitivityChart.options.plugins.annotation = {
                annotations: {
                    line1: {
                        type: 'line',
                        xMin: currentVal,
                        xMax: currentVal,
                        borderColor: '#ef4444',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        label: {
                            content: `Current: ${currentVal}`,
                            enabled: true,
                            position: 'top'
                        }
                    }
                }
            };
            
            sensitivityChart.update('none'); // Update without full redraw animation
        } else {
            // Create Chart
            const ctx = document.getElementById('sensitivityChart').getContext('2d');
            const cyan = getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim() || '#06b6d4';
            
            sensitivityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: `Calibrated Strength vs ${labelInfo.name} (${labelInfo.unit})`,
                        data: strengths,
                        borderColor: cyan,
                        borderWidth: 3,
                        pointRadius: 2,
                        pointHoverRadius: 6,
                        fill: true,
                        backgroundColor: 'rgba(6, 182, 212, 0.08)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'linear',
                            title: {
                                display: true,
                                text: `${labelInfo.name} (${labelInfo.unit})`,
                                color: '#94a3b8'
                            },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Strength (MPa)',
                                color: '#94a3b8'
                            },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#f8fafc' } },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `Calibrated Strength: ${context.parsed.y} MPa`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (err) {
        console.error("Failed to update sensitivity chart:", err);
    }
}

// Start application
window.addEventListener('DOMContentLoaded', init);
