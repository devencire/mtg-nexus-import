-- Tabletop Simulator Lua script for creating 15-card Booster packs
-- from a CustomDeck (cube.json). Full of Godshards-specific assumptions!
-- If you're reading this, forgive me for my programming sins. ada~

local function contains(str, phrase)
    return string.find(str, phrase, 1, true) ~= nil
end

local function categorizeCards(containedObjects)
    local commons = {}
    local uncommons = {}
    local rares = {}
    local mythics = {}
    local shards = {}

    for _, card in ipairs(containedObjects) do
        if contains(card.Nickname, "Godshard") then
            table.insert(shards, card)
        elseif contains(card.Description, "GDS-C") then
            table.insert(commons, card)
        elseif contains(card.Description, "GDS-U") then
            table.insert(uncommons, card)
        elseif contains(card.Description, "GDS-R") then
            table.insert(rares, card)
        elseif contains(card.Description, "GDS-M") then
            table.insert(mythics, card)
        end
    end

    return {
        commons = commons,
        uncommons = uncommons,
        rares = rares,
        mythics = mythics,
        shards = shards
    }
end

local function pickRandom(pool, count)
    local results = {}
    if not pool or #pool == 0 or count <= 0 then
        return results
    end

    for _ = 1, count do
        local idx = math.random(1, #pool)
        table.insert(results, pool[idx])
    end

    return results
end

local function selectBoosterCards(categories, numPacks)
    math.randomseed(os.time())

    local selected = {}

    for pack=1,numPacks do
        -- 1. 10 non-shard 'commons' (GDS-C, non-Godshard)
        local commons = pickRandom(categories.commons, 10)
        for _, card in ipairs(commons) do
            table.insert(selected, card)
        end

        -- 2. 3 non-shard 'uncommons' (GDS-U, non-Godshard)
        local uncommons = pickRandom(categories.uncommons, 3)
        for _, card in ipairs(uncommons) do
            table.insert(selected, card)
        end

        -- 3. 1 non-shard 'rare' (GDS-R) or 'mythic' (GDS-M)
        -- 12.5% chance mythic, 87.5% chance rare
        local rareOrMythicPool = categories.rares
        if math.random() < 0.125 then
            rareOrMythicPool = categories.mythics
        end
        local rareOrMythic = pickRandom(rareOrMythicPool, 1)
        for _, card in ipairs(rareOrMythic) do
            table.insert(selected, card)
        end

        -- 4. 1 shard (contains 'Godshard')
        local shard = pickRandom(categories.shards, 1)
        for _, card in ipairs(shard) do
            table.insert(selected, card)
        end
    end

    return selected
end

function shallowCopy(orig)
    local orig_type = type(orig)
    local copy
    if orig_type == 'table' then
        copy = {}
        for orig_key, orig_value in pairs(orig) do
            copy[orig_key] = orig_value
        end
    else
        -- number, string, boolean, etc
        copy = orig
    end
    return copy
end

function sanitiseCustomDeckTable(customDeck)
    local sanitisedCustomDeck = {}
    for i, item in pairs(customDeck) do
        sanitisedCustomDeck[tostring(i)] = item
    end
    return sanitisedCustomDeck
end

function spawnBooster(numPacks)
    local deckData = self.getData()
    local categories = categorizeCards(deckData.ContainedObjects)
    local selectedCards = selectBoosterCards(categories, numPacks)

    if #selectedCards == 0 then
        if log then
            log("Error: No cards could be selected for the booster pack.")
        end
        return
    end

    local boosterDeckIDs = {}
    local boosterContainedObjects = {}
    local boosterCustomDeck = sanitiseCustomDeckTable(deckData.CustomDeck)

    for _, card in ipairs(selectedCards) do
        local cardCopy = shallowCopy(card)
        cardCopy.GUID = ""
        cardCopy.CustomDeck = sanitiseCustomDeckTable(cardCopy.CustomDeck)
        table.insert(boosterContainedObjects, cardCopy)
        table.insert(boosterDeckIDs, tonumber(cardCopy.CardID))
    end

    local selfPos = self.getPosition()
    local selfRot = self.getRotation()
    local spawnPos = {
        x = selfPos.x,
        y = selfPos.y + 5,
        z = selfPos.z
    }
    local spawnRot = {
        x = selfRot.x,
        y = selfRot.y + 90,
        z = selfRot.z
    }

    local boosterData = {
        Name = "Deck",
        Transform = {
            posX = spawnPos.x,
            posY = spawnPos.y,
            posZ = spawnPos.z,
            rotX = spawnRot.x,
            rotY = spawnRot.y,
            rotZ = spawnRot.z,
            scaleX = 1.0,
            scaleY = 1.0,
            scaleZ = 1.0
        },
        Nickname = "Godshards Booster Pack",
        Description = "Per 15 cards: 10 commons, 3 uncommons, 1 rare (12.5% mythic), 1 Godshard",
        DeckIDs = boosterDeckIDs,
        CustomDeck = boosterCustomDeck,
        ContainedObjects = boosterContainedObjects,
        Hands = false,
        HideWhenFaceDown = true,
        SidewaysCard = false,
        Grid = true,
        Snap = true,
        DragSelectable = true,
        Autoraise = true,
        Sticky = true,
        Tooltip = true,
        GUID = "",
    }

    log(boosterData)

    spawnObjectData({
        data = boosterData,
        position = spawnPos,
        rotation = spawnRot
    })
end

function spawnSingleBooster()
    spawnBooster(1)
end

function spawnSixBoosters()
    spawnBooster(6)
end

function resetContextMenu()
    self.clearContextMenu()
    self.addContextMenuItem("Make Booster Pack", spawnSingleBooster)
    self.addContextMenuItem("Make 6 Booster Packs", spawnSixBoosters)
end

function onLoad(save_state)
    resetContextMenu()
end

function onSpawn()
    resetContextMenu()
end

function onNumberTyped(_, number)
    spawnBooster(number)
    return true
end
