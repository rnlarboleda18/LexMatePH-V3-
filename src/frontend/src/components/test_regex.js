const regex = /^[^\w]*\([a-z0-9]+\)/i;
const testCase = "(1) ADMINISTRATIVE ORGANIZATION;";
console.log("Test 1:", regex.test(testCase)); 

const testCase2 = "   (1) ADMINISTRATIVE ORGANIZATION;";
console.log("Test 2:", regex.test(testCase2));

const testCase3 = "\u00A0(1) ADMINISTRATIVE ORGANIZATION;";
console.log("Test 3:", regex.test(testCase3));

const testCase4 = "\u200C(1) ADMINISTRATIVE ORGANIZATION;";
console.log("Test 4:", regex.test(testCase4));
