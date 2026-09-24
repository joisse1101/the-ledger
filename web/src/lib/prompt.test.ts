import { describe, expect, it } from "vitest";
import { answerValue, buildAnswers, emptySelection, parseQuestions } from "./prompt";
import type { PromptQuestion } from "./prompt";

const single: PromptQuestion = {
  question: "Which database?",
  header: "DB",
  options: [
    { label: "sqlite", description: "" },
    { label: "postgres", description: "" },
  ],
  multiSelect: false,
};
const multi: PromptQuestion = { ...single, question: "Which extras?", multiSelect: true };

describe("parseQuestions", () => {
  it("reads questions, options and multiSelect", () => {
    const parsed = parseQuestions({
      questions: [
        { question: "Which database?", header: "DB", options: [{ label: "sqlite", description: "small" }] },
        { question: "Extras?", options: [{ label: "auth" }, { label: "logs" }], multiSelect: true },
      ],
    });
    expect(parsed).toEqual([
      { question: "Which database?", header: "DB", options: [{ label: "sqlite", description: "small" }], multiSelect: false },
      {
        question: "Extras?",
        header: "",
        options: [
          { label: "auth", description: "" },
          { label: "logs", description: "" },
        ],
        multiSelect: true,
      },
    ]);
  });

  it.each([
    ["no questions key", {}],
    ["an empty list", { questions: [] }],
    ["a non-object entry", { questions: ["nope"] }],
    ["a blank question", { questions: [{ question: "  ", options: [] }] }],
  ])("returns null for %s", (_name, input) => {
    expect(parseQuestions(input)).toBeNull();
  });
});

describe("answerValue", () => {
  it("needs exactly one pick for a single-choice question", () => {
    expect(answerValue(single, emptySelection)).toBeNull();
    expect(answerValue(single, { ...emptySelection, picked: ["postgres"] })).toBe("postgres");
  });

  it("uses trimmed free text when Other is chosen, and refuses it blank", () => {
    expect(answerValue(single, { picked: [], otherOn: true, other: "  duckdb " })).toBe("duckdb");
    expect(answerValue(single, { picked: [], otherOn: true, other: "   " })).toBeNull();
  });

  it("returns an array for a multi-select, with free text appended", () => {
    expect(answerValue(multi, emptySelection)).toBeNull();
    expect(answerValue(multi, { ...emptySelection, picked: ["auth", "logs"] })).toEqual(["auth", "logs"]);
    expect(answerValue(multi, { picked: ["auth"], otherOn: true, other: "metrics" })).toEqual(["auth", "metrics"]);
    expect(answerValue(multi, { picked: ["auth"], otherOn: true, other: "" })).toBeNull();
  });
});

describe("buildAnswers", () => {
  it("keys each answer by its question text", () => {
    expect(
      buildAnswers(
        [single, multi],
        [
          { ...emptySelection, picked: ["sqlite"] },
          { ...emptySelection, picked: ["auth", "logs"] },
        ],
      ),
    ).toEqual({ "Which database?": "sqlite", "Which extras?": ["auth", "logs"] });
  });

  it("is null until every question is answered", () => {
    expect(buildAnswers([single, multi], [{ ...emptySelection, picked: ["sqlite"] }])).toBeNull();
  });
});
