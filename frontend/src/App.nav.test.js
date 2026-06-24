import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";


describe("App navigation labels", () => {
  it("routes unauthenticated users through feature-preview onboarding and signup setup", () => {
    const appVue = readFileSync(new URL("./App.vue", import.meta.url), "utf8");
    const onboardingVue = readFileSync(new URL("./views/OnboardingView.vue", import.meta.url), "utf8");

    assert.match(appVue, /OnboardingView/);
    assert.match(appVue, /v-else-if="!isAuthenticated"/);
    assert.match(onboardingVue, /featurePreviewGrid/);
    assert.match(onboardingVue, /VEHICLE_FUEL_LABELS/);
    assert.match(onboardingVue, /VehicleTypePicker/);
    assert.match(onboardingVue, /smartfuel:onboarding-draft/);
    assert.match(onboardingVue, /addVehicle/);
    assert.match(onboardingVue, /signupAccount/);
    assert.doesNotMatch(onboardingVue, /checkUsername|socialLogin|guestMode/);
  });

  it("consolidates duplicated top navigation into the left sidebar", () => {
    const appVue = readFileSync(new URL("./App.vue", import.meta.url), "utf8");
    const sidebarVue = readFileSync(new URL("./components/DoubleSidebar.vue", import.meta.url), "utf8");

    assert.doesNotMatch(appVue, />내 차량 설정</);
    assert.doesNotMatch(appVue, />할인 카드 관리</);
    assert.doesNotMatch(appVue, />커뮤니티</);
    assert.doesNotMatch(appVue, />로그인</);
    assert.doesNotMatch(appVue, />로그아웃</);
    assert.doesNotMatch(appVue, />회원 가입</);
    assert.match(appVue, /v-if="isAuthenticated" class="userIndicator"/);
    assert.match(appVue, /auth\.user\.username/);

    assert.match(sidebarVue, />위치</);
    assert.match(sidebarVue, />나의 환경</);
    assert.match(sidebarVue, />선정 방식</);
    assert.match(sidebarVue, />커뮤니티</);
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
      "검색 반경",
      "빠른 설정 변경",
      "priorityPocketTabs",
      "맞춤 추천 검색"
    ];
    const markerIndexes = orderedMarkers.map((marker) => locationSection.indexOf(marker));

    assert.ok(markerIndexes.every((index) => index >= 0));
    assert.deepEqual(
      markerIndexes,
      [...markerIndexes].sort((a, b) => a - b)
    );
    assert.doesNotMatch(locationSection, /quickRecommendationPanel/);
    const priorityMarkers = [">최적</", ">가격</", ">거리</"];
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
    assert.doesNotMatch(locationControl, /장소 추가/);
    assert.doesNotMatch(locationControl, /openPresetAddTab/);
    assert.match(locationControl, /@click="openPresetEditor\('home'\)"/);
    assert.match(locationControl, /@click="openPresetEditor\('work'\)"/);
    assert.match(locationControl, /v-if="activePresetEditor" class="presetEditorPanel"/);
    assert.match(locationControl, /@click="confirmPresetSave\(activePresetEditor\)"/);
    assert.doesNotMatch(locationControl, /@dblclick/);
  });
});
