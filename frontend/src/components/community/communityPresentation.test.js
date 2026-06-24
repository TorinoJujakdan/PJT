import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  canEditPost,
  formatCommunityError,
  getStarredButtonLabel,
  parseTagInput,
  removePostById,
  replacePostById,
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
      formatCommunityError({ payload: { code: "INVALID_COMMUNITY_POST" } }),
      "게시글 입력값을 확인해 주세요.",
    );
  });

  it("replaces or removes posts by id without mutating unrelated cards", () => {
    const posts = [
      { id: 1, title: "one", is_starred: false },
      { id: 2, title: "two", is_starred: false },
    ];

    assert.deepEqual(replacePostById(posts, { id: 2, is_starred: true }), [
      { id: 1, title: "one", is_starred: false },
      { id: 2, title: "two", is_starred: true },
    ]);
    assert.deepEqual(removePostById(posts, 1), [{ id: 2, title: "two", is_starred: false }]);
  });

  it("labels the private star action from the current post state", () => {
    assert.equal(getStarredButtonLabel({ is_starred: true }), "별표 해제");
    assert.equal(getStarredButtonLabel({ is_starred: false }), "별표 저장");
  });
});
