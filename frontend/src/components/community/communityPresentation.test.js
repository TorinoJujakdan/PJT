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
      "\uc791\uc131\uc790\ub9cc \uc218\uc815\ud558\uac70\ub098 \uc0ad\uc81c\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
    );
    assert.equal(
      formatCommunityError({ payload: { code: "INVALID_COMMUNITY_POST" } }),
      "\ubd80\uc801\uc808\ud55c \uba54\uc138\uc9c0 \uc785\ub2c8\ub2e4",
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
    assert.equal(getStarredButtonLabel({ is_starred: true }), "\ubcc4\ud45c \ud574\uc81c");
    assert.equal(getStarredButtonLabel({ is_starred: false }), "\ubcc4\ud45c \uc800\uc7a5");
  });
});
