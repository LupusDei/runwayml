# The formula — 90 seconds that are funny first and true always

**Primary purpose: entertain. Secondary: teach.** A beat that is correct but not fun has failed.
Written for 3–6 year olds. Older audiences take the same shape with more facts per beat.

## Shape: six scenes × 15 s

| Scene | Job |
|---|---|
| 1 | **Hook.** Greet every child by name. Set up the trip ("Hop in the time rocket!"). Say in one line what the topic *is* ("A president leads the whole country"). Give the first fact. |
| 2–5 | **Beats.** One or two facts each. |
| 6 | **Payoff.** Recap the whole list out loud (repetition is how small children learn). Make a callback to the running gag. Sign off warmly by name. |

## Longer episodes: twelve scenes × 15 s = three minutes

At three minutes the shape is the same, but the episode needs a **spine**: something that carries the child from
scene to scene. A list of facts cannot hold a three-year-old for 180 seconds; a story can.

| Scenes | Job |
|---|---|
| 1 | **Hook.** Names, and the question as a guessing game ("Is it a rocket? No! A cheetah? No! It's… light!"). |
| 2–3 | **Make the idea physical, close to home.** Something they can feel: a snap, one second, the Moon. |
| 4 | **Start the journey.** A race, a trip, a hunt: one goal the rest of the episode travels towards. |
| 5–6 | **Beats on the way.** One fact each, each with an everyday comparison (brushing teeth, a car ride). |
| 7 | **The midpoint.** A participation beat ("Who's the fastest? Say it with me!") and a callback to an earlier episode. It resets attention, and small children love being in on it. |
| 8–10 | **Escalate.** Every stop farther, bigger, sillier. The running gag builds: tired → asleep → cinema seats → scarf. |
| 11 | **The wonder beat.** One idea that is bigger than the rest, said quietly ("you're seeing light that left long, long ago"). |
| 12 | **Payoff.** Recap the key numbers as a chant, a callback to the gag, and the sign-off by name. |

**Teach one idea from many angles** rather than many ideas once. The speed-of-light episode says "light is
fastest" nine different ways; that is the lesson, and the planets are only the ruler.

**Use an everyday measure the child already has** for every number: a snap for a second, brushing teeth for
minutes, a movie for an hour, an afternoon for hours, a birthday for years.

## Every beat has three parts

1. **One true, checkable fact.** Choose the *weird* true fact over the important one. "Jackson got a cheese as
   big as a table" beats "Jackson was a general". Children remember the cheese, and the name rides along with it.
2. **A comparison a small child can picture.** Bathtub, table, a ball rolling, a sneeze. Never numbers.
3. **A physical gag with the companion.** The unicorn gets licked by a dog, gets a brain freeze, cannonballs
   into the river, nibbles through the cheese. Escalate it across the episode.

## Devices that worked (planets → presidents)

- **A vehicle and a trip.** It gives every scene a reason to move and every cut a place to go.
- **A counting spine for ordered lists.** "Number one… number two…" teaches the order for free.
- **One participation beat.** "Can you say it? O-K!" Children talk back to the screen, so let them.
- **A running prop into the ending.** The unicorn falls asleep still hugging the cheese.
- **Sound words she can play with.** "Ooh, toasty!", "Achoo!", "Splash!", "Yum!"

## Writing rules

The validator enforces the first four.

- **34 spoken words per scene or fewer.** More and the character rushes to fit.
- **Numbers as words.** "Eight", not "8".
- **The first and last scenes say every name**, spelled as in the audience file.
- **The prompt stays under 1000 characters**, including the character's `look`.
- Short sentences and exclamations.
- Nothing a child could copy dangerously (no "breathe the helium").
- Myths are not facts. If historians dispute it, pick another fact.
- **Every scene carries a `fact_check`**: the number and where it came from, or "no factual claims". The
  validator requires it, because the check has to be written down to be done at all.

## Picture rules

- **No text anywhere.** The models write gibberish; every prompt ends by forbidding it.
- **Don't ask the picture to count past about three.** The model can't count. The words carry the numbers.
- **Real historical people appear as friendly generic cartoon figures**, described by costume ("a very tall
  gentleman in a long blue coat"), not as portraits. The facts are the point, and the model would otherwise
  invent a face and present it as the real person.
- **Plain, unmarked vehicles.** No flags, badges or plates, because those are text again.
- **Props that usually carry writing get writing.** A cinema popcorn bucket came out with "POP" on it. Say
  "a plain striped popcorn bucket with no writing". The same goes for books, signs, boxes and jerseys.
- **Name every drifting trait in the character's `look`.**
- **A prop that recurs across scenes drifts unless it has a reference image.** The robot in the robots episode
  was a box, then a humanoid, then a camera-headed cart; words alone did not hold it. If the prop is the star
  of the episode, make it a **guest** (PLAYBOOK §1): one `gen4_image` still, then every scene uses it. If it is
  meant to change (a robot being built), make the change part of the story so the drift reads as progress.

## Sound rules

- Put the effects in `sfx` and they are generated with the action, in sync.
- Scenes have no music. One bed runs under the whole episode and ducks under the voice.
