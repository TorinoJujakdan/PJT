import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";


describe("App navigation labels", () => {
  it("routes unauthenticated users through one-page onboarding and lightweight signup", () => {
    const appVue = readFileSync(new URL("./App.vue", import.meta.url), "utf8");
    const onboardingVue = readFileSync(new URL("./views/OnboardingView.vue", import.meta.url), "utf8");

    assert.match(appVue, /OnboardingView/);
    assert.match(appVue, /v-else-if="!isAuthenticated"/);
    assert.match(onboardingVue, /landingHero/);
    assert.match(onboardingVue, /EXPECTED EFFECTS/);
    assert.match(onboardingVue, /SERVICE INTRO/);
    assert.match(onboardingVue, /HOW IT WORKS/);
    assert.match(onboardingVue, /signupAndAuthenticate/);
    assert.match(onboardingVue, /onboarding-signup/);
    const accountsApi = readFileSync(new URL("./api/accounts.js", import.meta.url), "utf8");
    assert.match(accountsApi, /signupAndAuthenticate/);
    assert.match(accountsApi, /getCurrentUser/);
    assert.match(accountsApi, /loginAccount/);
    assert.doesNotMatch(onboardingVue, /VEHICLE_FUEL_LABELS|VehicleTypePicker|smartfuel:onboarding-draft|addVehicle/);
    assert.doesNotMatch(onboardingVue, /checkUsername|socialLogin|guestMode/);
  });

  it("consolidates duplicated top navigation into the left sidebar", () => {
    const appVue = readFileSync(new URL("./App.vue", import.meta.url), "utf8");
    const sidebarVue = readFileSync(new URL("./components/DoubleSidebar.vue", import.meta.url), "utf8");

    for (const label of ["\uB0B4 \uCC28\uB7C9 \uC124\uC815", "\uD560\uC778 \uCE74\uB4DC \uAD00\uB9AC", "\uCEE4\uBBA4\uB2C8\uD2F0", "\uB85C\uADF8\uC778", "\uB85C\uADF8\uC544\uC6C3", "\uD68C\uC6D0 \uAC00\uC785"]) {
      assert.doesNotMatch(appVue, new RegExp(`>${label}<`));
    }
    assert.match(appVue, /v-if="isAuthenticated" class="userIndicator"/);
    assert.match(appVue, /auth\.user\.username/);

    for (const label of ["\uC704\uCE58", "\uB098\uC758 \uD658\uACBD", "\uC120\uC815 \uBC29\uC2DD", "\uCEE4\uBBA4\uB2C8\uD2F0"]) {
      assert.match(sidebarVue, new RegExp(`>${label}<`));
    }
    assert.match(sidebarVue, /emit\('open-community'\)/);
    assert.match(appVue, /@open-community="openModal\('community'\)"/);
    assert.match(appVue, /activeModal === 'community'/);
  });

  it("orders the location tab controls and keeps priority choices as compact pocket tabs", () => {
    const sidebarVue = readFileSync(new URL("./components/DoubleSidebar.vue", import.meta.url), "utf8");
    const locationStart = sidebarVue.indexOf("<template v-if=\"activeTab === 'location'\">");
    const locationEnd = sidebarVue.indexOf("</template>", locationStart);
    const locationSection = sidebarVue.slice(locationStart, locationEnd);

    const orderedMarkers = [
      "<LocationControl",
      "<FuelTargetControl",
      "\uAC80\uC0C9 \uBC18\uACBD",
      "\uBE60\uB978 \uC124\uC815 \uBCC0\uACBD",
      "priorityPocketTabs",
      "\uB9DE\uCDA4 \uCD94\uCC9C \uAC80\uC0C9"
    ];
    const markerIndexes = orderedMarkers.map((marker) => locationSection.indexOf(marker));

    assert.ok(markerIndexes.every((index) => index >= 0));
    assert.deepEqual(
      markerIndexes,
      [...markerIndexes].sort((a, b) => a - b)
    );
    assert.doesNotMatch(locationSection, /quickRecommendationPanel/);
    const priorityMarkers = [">\uCD5C\uC801<", ">\uAC00\uACA9<", ">\uAC70\uB9AC<"];
    const priorityIndexes = priorityMarkers.map((marker) => locationSection.indexOf(marker));
    assert.ok(priorityIndexes.every((index) => index >= 0));
    assert.deepEqual(
      priorityIndexes,
      [...priorityIndexes].sort((a, b) => a - b)
    );
    assert.doesNotMatch(locationSection, /<small>/);
  });

  it("places home and company quick tabs above address search with editor tabs", () => {
    const locationControl = readFileSync(new URL("./components/LocationControl.vue", import.meta.url), "utf8");
    const presetIndex = locationControl.indexOf("presetActions");
    const searchIndex = locationControl.indexOf("searchControl");

    assert.ok(presetIndex >= 0);
    assert.ok(searchIndex >= 0);
    assert.ok(presetIndex < searchIndex);
    assert.match(locationControl, /@click="usePreset\('home'\)"/);
    assert.match(locationControl, /@click="usePreset\('work'\)"/);
    assert.doesNotMatch(locationControl, /\uC7A5\uC18C \uCD94\uAC00/);
    assert.doesNotMatch(locationControl, /openPresetAddTab/);
    assert.match(locationControl, /@click="openPresetEditor\('home'\)"/);
    assert.match(locationControl, /@click="openPresetEditor\('work'\)"/);
    assert.match(locationControl, /v-if="activePresetEditor" class="presetEditorPanel"/);
    assert.match(locationControl, /@click="confirmPresetSave\(activePresetEditor\)"/);
    assert.doesNotMatch(locationControl, /@dblclick/);
  });
});
