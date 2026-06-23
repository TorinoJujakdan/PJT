import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  canEditPost,
  formatCommunityError,
  parseTagInput,
  tagsToInput,
} from "./communityPresentation.js";


describe("communityPresentation", () => {
  it("parses comma separated tags with trimming, dedupe, and max bound", () => {
    const tags = parseTagInput(" clean, coffee, clean, , kind, a,b,c,d,e,f,g,h,i ");

    assert.deepEqual(tags, ["clean", "coffee", "kind", "a", "b", "c", "d", "e", "f", "g"]);
  });

  it("serializes tags for edit forms", () => {
    assert.equal(tagsToInput(["clean", "coffee"]), "clean, coffee");
  });

  it("prefers backend can_edit but can infer from user when absent", () => {
    assert.equal(canEditPost({ can_edit: false, author: { id: 1 } }, { id: 1 }), false);
    assert.equal(canEditPost({ author: { id: 1 } }, { id: 1 }), true);
    assert.equal(canEditPost({ author: { id: 2 } }, { id: 1 }), false);
  });

  it("maps contract error codes to user-facing guidance", () => {
    assert.equal(
      formatCommunityError({ payload: { code: "COMMUNITY_POST_FORBIDDEN" } }),
      "작성자만 수정하거나 삭제할 수 있습니다.",
    );
    assert.equal(
      formatCommunityError({ payload: { code: "STATION_NOT_FOUND" } }),
      "해당 주유소를 찾을 수 없습니다. 주유소 ID를 확인해 주세요.",
    );
  });
});
