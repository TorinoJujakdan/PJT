const NAVER_MAPS_SCRIPT_ID = "naver-maps-script";

let loadingPromise = null;

export function getNaverMapsClientId() {
  return import.meta.env.VITE_NAVER_MAPS_CLIENT_ID || "";
}

export function hasNaverMaps() {
  return Boolean(window.naver?.maps);
}

export function loadNaverMapsScript(clientId = getNaverMapsClientId()) {
  if (!clientId) {
    return Promise.reject(new Error("NAVER_MAPS_CLIENT_ID_MISSING"));
  }

  if (hasNaverMaps()) {
    return Promise.resolve(window.naver.maps);
  }

  if (loadingPromise) {
    return loadingPromise;
  }

  loadingPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById(NAVER_MAPS_SCRIPT_ID);
    const script = existingScript || document.createElement("script");

    script.id = NAVER_MAPS_SCRIPT_ID;
    script.async = true;
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(clientId)}`;

    script.addEventListener(
      "load",
      () => {
        if (hasNaverMaps()) {
          resolve(window.naver.maps);
          return;
        }
        reject(new Error("NAVER_MAPS_LOAD_FAILED"));
      },
      { once: true }
    );
    script.addEventListener(
      "error",
      () => reject(new Error("NAVER_MAPS_LOAD_FAILED")),
      { once: true }
    );

    if (!existingScript) {
      document.head.appendChild(script);
    }
  }).catch((error) => {
    loadingPromise = null;
    throw error;
  });

  return loadingPromise;
}
