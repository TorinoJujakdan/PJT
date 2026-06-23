import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";


describe("App navigation labels", () => {
  it("keeps the public community tab and authenticated nav labels readable", () => {
    const appVue = readFileSync(new URL("./App.vue", import.meta.url), "utf8");

    assert.match(appVue, />내 차량 설정</);
    assert.match(appVue, />할인 카드 관리</);
    assert.match(appVue, />커뮤니티</);
    assert.match(appVue, /activeModal === 'community'/);
  });
});
