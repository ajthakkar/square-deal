import { test } from "node:test";
import assert from "node:assert/strict";

import { canonicalStreet, matchStreets, miles, parseAddress, type StreetEntry } from "../src/lib/homes.ts";

test("county short forms and typed spellings meet in the middle", () => {
  assert.equal(canonicalStreet("RIVERSIDE WY"), canonicalStreet("Riverside Way"));
  assert.equal(canonicalStreet("WORTHINGTON WOODS BL"), "WORTHINGTON WOODS BLVD");
  assert.equal(canonicalStreet("west Pacemont road"), "W PACEMONT RD");
  assert.equal(canonicalStreet("BARNETT CT S"), canonicalStreet("Barnett Court South"));
  assert.equal(canonicalStreet("COURT ST"), "COURT ST"); // a street named Court stays Court
});

test("parses a full mailing-style address", () => {
  assert.deepEqual(parseAddress("86 W. Pacemont Road, Columbus, OH 43202"), { number: 86, street: "W PACEMONT RD", zip: "43202" });
  assert.deepEqual(parseAddress("872 - 874 Summit St"), { number: 872, street: "SUMMIT ST", zip: null });
  assert.equal(parseAddress("1500 Oak Lane Apt 4").street, "OAK LN");
});

test("exact street first, ZIP breaks ties", () => {
  const s = (street: string, zips: string[]): StreetEntry => ({ street, shard: 0, zips, cities: [] });
  const streets = [s("N HIGH ST", ["43215"]), s("HIGH ST", ["43085"]), s("S HIGH ST", ["43207"]), s("HIGHLAND AVE", ["43212"])];
  assert.equal(matchStreets(streets, "N HIGH ST", null)[0].street, "N HIGH ST");
  assert.equal(matchStreets(streets, "HIGH ST", "43085")[0].street, "HIGH ST");
  assert.ok(matchStreets(streets, "HIGHL", null).some((e) => e.street === "HIGHLAND AVE"));
});

test("distance", () => {
  // Ohio Stadium to the Statehouse is about 2.8 miles in a straight line
  const d = miles([40.0017, -83.0197], [39.9612, -82.9988]);
  assert.ok(d > 2.5 && d < 3.1, String(d));
});
