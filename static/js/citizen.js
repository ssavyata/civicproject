var _photoFiles = [];   /* our authoritative file list */
var MAX_PHOTOS  = 5;
var MAX_MB      = 5;

function previewImages(event) {
  var incoming = Array.from(event.target.files);
  var container = document.getElementById('image-preview');
  var input     = document.getElementById('id_photos');
  if (!container || !input) return;

  /* 1. Validate and merge, avoiding duplicates by name+size */
  var errors = [];
  incoming.forEach(function (file) {
    if (file.size > MAX_MB * 1024 * 1024) {
      errors.push(file.name + ' is over ' + MAX_MB + ' MB and was skipped.');
      return;
    }
    var already = _photoFiles.some(function (f) {
      return f.name === file.name && f.size === file.size;
    });
    if (already) return;
    if (_photoFiles.length >= MAX_PHOTOS) {
      errors.push('Maximum ' + MAX_PHOTOS + ' photos allowed. "' + file.name + '" was skipped.');
      return;
    }
    _photoFiles.push(file);
  });

  /* 2. Sync DataTransfer → input so the form actually submits the files */
  _syncInputFiles(input);

  /* 3. Re-render the whole preview grid */
  _renderPreviews(container, input);

  /* 4. Show any errors */
  var errBox = document.getElementById('photo-errors');
  if (errBox) {
    errBox.innerHTML = errors.map(function (e) {
      return '<p class="field__error">' + e + '</p>';
    }).join('');
  }
}

function _removePhoto(index, input) {
  _photoFiles.splice(index, 1);
  _syncInputFiles(input);
  var container = document.getElementById('image-preview');
  if (container) _renderPreviews(container, input);
  var errBox = document.getElementById('photo-errors');
  if (errBox) errBox.innerHTML = '';
}

function _syncInputFiles(input) {
  var dt = new DataTransfer();
  _photoFiles.forEach(function (f) { dt.items.add(f); });
  input.files = dt.files;
}

function _renderPreviews(container, input) {
  container.innerHTML = '';

  /* Counter badge */
  var counter = document.getElementById('photo-counter');
  if (counter) {
    counter.textContent = _photoFiles.length + ' / ' + MAX_PHOTOS;
    counter.style.color = _photoFiles.length >= MAX_PHOTOS ? '#dc2626' : '#6b7280';
  }

  _photoFiles.forEach(function (file, index) {
    var reader = new FileReader();
    reader.onload = function (e) {

      /* Wrapper */
      var wrap = document.createElement('div');
      wrap.style.cssText = 'position:relative;width:100px;flex-shrink:0;';

      /* Thumbnail */
      var img = document.createElement('img');
      img.src           = e.target.result;
      img.alt           = file.name;
      img.style.cssText = 'width:100px;height:100px;object-fit:cover;'
                        + 'border-radius:8px;border:2px solid #6ee7b7;display:block;';

      /* Remove button — ✕ overlaid top-right */
      var btn = document.createElement('button');
      btn.type          = 'button';
      btn.title         = 'Remove ' + file.name;
      btn.style.cssText = 'position:absolute;top:-8px;right:-8px;'
                        + 'width:22px;height:22px;border-radius:50%;'
                        + 'background:#dc2626;border:2px solid #fff;'
                        + 'color:#fff;font-size:12px;font-weight:700;'
                        + 'line-height:1;cursor:pointer;display:flex;'
                        + 'align-items:center;justify-content:center;'
                        + 'padding:0;z-index:10;';
      btn.textContent   = '✕';
      btn.addEventListener('click', function () { _removePhoto(index, input); });

      /* Filename label */
      var lbl = document.createElement('p');
      lbl.style.cssText = 'font-size:0.6rem;color:#6b7280;max-width:100px;'
                        + 'overflow:hidden;text-overflow:ellipsis;'
                        + 'white-space:nowrap;margin-top:4px;text-align:center;';
      lbl.textContent   = file.name;

      wrap.appendChild(img);
      wrap.appendChild(btn);
      wrap.appendChild(lbl);
      container.appendChild(wrap);
    };
    reader.readAsDataURL(file);
  });
}

/* ── togglePwd also needs global scope (called via onclick attribute) ── */
function togglePwd(inputId) {
  var input = document.getElementById(inputId);
  if (!input) return;
  var hiding = input.type === 'password';
  input.type = hiding ? 'text' : 'password';
  var wrap = input.closest('.field__pwd-wrap');
  var icon = wrap && wrap.querySelector('.material-symbols-outlined');
  if (icon) icon.textContent = hiding ? 'visibility_off' : 'visibility';
}

/* ── everything that touches the DOM on load lives here ── */
document.addEventListener('DOMContentLoaded', function () {

  /* reset file list in case of bfcache restore */
  _photoFiles = [];
  var inp = document.getElementById('id_photos');
  if (inp) { try { inp.files = new DataTransfer().files; } catch(e){} }

  var mapEl = document.getElementById('location-map');

  if (mapEl) {
    if (typeof L === 'undefined') {
      console.error('CivicReport: Leaflet (L) is not defined. Check script load order.');
    } else {
      var DEFAULT_LAT  = 28.2096;
      var DEFAULT_LNG  = 83.9856;
      var DEFAULT_ZOOM = 15;

      var latInput  = document.getElementById('location-lat');
      var lngInput  = document.getElementById('location-lng');
      var textInput = document.getElementById('location-text');
      var addrEl    = document.getElementById('location-address');
      var coordsEl  = document.getElementById('location-coords');
      var displayEl = document.getElementById('location-display');
      var instrEl   = document.getElementById('map-instruction');

      var savedLat = latInput  && latInput.value  ? parseFloat(latInput.value)  : null;
      var savedLng = lngInput  && lngInput.value  ? parseFloat(lngInput.value)  : null;
      var hasSaved = !!(savedLat && savedLng);

      var map = L.map('location-map', { zoomControl: true })
                 .setView(
                   [hasSaved ? savedLat : DEFAULT_LAT, hasSaved ? savedLng : DEFAULT_LNG],
                   DEFAULT_ZOOM
                 );

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19
      }).addTo(map);

      var pinIcon = L.divIcon({
        className : 'civic-pin',
        html      : '<span class="material-symbols-outlined" '
                  + 'style="font-size:2.25rem;color:#065f46;'
                  + 'text-shadow:0 2px 6px rgba(0,0,0,.3);line-height:1;">'
                  + 'location_on</span>',
        iconSize  : [36, 36],
        iconAnchor: [18, 36],
      });

      var marker = null;

      function showDisplay() { if (displayEl) displayEl.style.display = 'flex'; }
      function hideDisplay() { if (displayEl) displayEl.style.display = 'none'; }
      function hideInstr()   { if (instrEl)   instrEl.style.display   = 'none'; }
      function showInstr()   { if (instrEl)   instrEl.style.display   = 'flex'; }

      function fillFields(lat, lng) {
        if (latInput)  latInput.value  = lat.toFixed(6);
        if (lngInput)  lngInput.value  = lng.toFixed(6);
        if (coordsEl)  coordsEl.textContent = lat.toFixed(5) + ', ' + lng.toFixed(5);
        showDisplay();
        hideInstr();
      }

      function placePin(lat, lng) {
        if (marker) {
          marker.setLatLng([lat, lng]);
        } else {
          marker = L.marker([lat, lng], { icon: pinIcon, draggable: true }).addTo(map);
          marker.on('dragend', function () {
            var p = marker.getLatLng();
            fillFields(p.lat, p.lng);
            geocode(p.lat, p.lng);
          });
        }
        fillFields(lat, lng);
      }

      function clearPin() {
        if (marker) { map.removeLayer(marker); marker = null; }
        if (latInput)  latInput.value  = '';
        if (lngInput)  lngInput.value  = '';
        if (textInput) textInput.value = '';
        if (addrEl)    addrEl.textContent   = '—';
        if (coordsEl)  coordsEl.textContent = '—';
        hideDisplay();
        showInstr();
      }

      function geocode(lat, lng) {
        if (addrEl) addrEl.textContent = 'Looking up address…';
        fetch(
          'https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat='
          + lat + '&lon=' + lng,
          { headers: { 'Accept-Language': 'en' } }
        )
        .then(function (r)    { return r.json(); })
        .then(function (data) {
          var addr = data.display_name || (lat.toFixed(5) + ', ' + lng.toFixed(5));
          if (addrEl)    addrEl.textContent = addr;
          if (textInput) textInput.value    = addr;
        })
        .catch(function () {
          var fb = lat.toFixed(5) + ', ' + lng.toFixed(5);
          if (addrEl)    addrEl.textContent = fb;
          if (textInput) textInput.value    = fb;
        });
      }

      map.on('click', function (e) {
        placePin(e.latlng.lat, e.latlng.lng);
        geocode(e.latlng.lat, e.latlng.lng);
      });

      var locBtn = document.getElementById('locate-me-btn');
      if (locBtn) {
        locBtn.addEventListener('click', function () {
          if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
          }
          locBtn.disabled    = true;
          locBtn.textContent = 'Locating…';
          navigator.geolocation.getCurrentPosition(
            function (pos) {
              var lat = pos.coords.latitude;
              var lng = pos.coords.longitude;
              map.setView([lat, lng], 17);
              placePin(lat, lng);
              geocode(lat, lng);
              locBtn.disabled  = false;
              locBtn.innerHTML = '<span class="material-symbols-outlined">my_location</span>'
                               + ' Use my current location';
            },
            function () {
              alert('Could not get your location. Please allow location access.');
              locBtn.disabled  = false;
              locBtn.innerHTML = '<span class="material-symbols-outlined">my_location</span>'
                               + ' Use my current location';
            },
            { timeout: 10000 }
          );
        });
      }

      var clrBtn = document.getElementById('clear-pin-btn');
      if (clrBtn) clrBtn.addEventListener('click', clearPin);

      if (hasSaved) {
        placePin(savedLat, savedLng);
        var savedText = textInput && textInput.value;
        if (savedText) {
          if (addrEl) addrEl.textContent = savedText;
        } else {
          geocode(savedLat, savedLng);
        }
      } else {
        hideDisplay();
      }

      /* let the browser finish layout before Leaflet measures the container */
      setTimeout(function () { map.invalidateSize(); }, 300);
    }
  }

  document.querySelectorAll('.alert--success, .alert--info').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity 0.5s ease';
      el.style.opacity    = '0';
      setTimeout(function () { el.remove(); }, 500);
    }, 4000);
  });

});