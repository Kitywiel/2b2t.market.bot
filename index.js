// index.js - Discord.js v14 minimal bot with buttons & modal and local CSV storage
require("dotenv").config();
const fs = require("fs");
const path = require("path");
const {
  Client,
  GatewayIntentBits,
  Partials,
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  AttachmentBuilder
} = require("discord.js");

// Optional keep-alive for Replit / similar
try { require("./keep_alive"); } catch (e) { /* optional */ }
try {require("./keep_alive_webhook");} catch (e) { console.warn("keep_alive_webhook failed:", e); }

const BOT_PREFIX = process.env.BOT_PREFIX || "!";
const TOKEN = process.env.BOT_TOKEN;
if (!TOKEN) {
  console.error("Missing BOT_TOKEN in environment");
  process.exit(1);
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ],
  partials: [Partials.Channel]
});

const SUBMISSIONS_FILE = path.resolve(__dirname, "submissions.csv");

// Utility: append a csv-safe quoted row
function appendCsvRow(fields) {
  const safe = fields.map(f => {
    if (f === null || f === undefined) return '""';
    return `"${String(f).replace(/"/g, '""')}"`;
  });
  fs.appendFileSync(SUBMISSIONS_FILE, safe.join(",") + "\n", { encoding: "utf8", flag: "a" });
}

// Commands via message prefix
client.on("messageCreate", async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith(BOT_PREFIX)) return;

  const args = message.content.slice(BOT_PREFIX.length).trim().split(/\s+/);
  const cmd = args.shift().toLowerCase();

  if (cmd === "ping") {
    const sent = await message.channel.send("Pinging...");
    const latency = sent.createdTimestamp - message.createdTimestamp;
    await sent.edit(`Pong! Latency: ${latency}ms`);
  }

  else if (cmd === "echo") {
    const text = args.join(" ");
    if (!text) return message.channel.send("Usage: !echo <text>");
    await message.channel.send(text);
  }

  else if (cmd === "menu") {
    const embed = new EmbedBuilder()
      .setTitle("Test Menu")
      .setDescription("Press a button below to open the form, say hi, or preview local submissions.")
      .setColor(0x5865F2)
      .addFields({ name: "Note", value: "Submissions are saved to submissions.csv for local testing." });

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("open_form").setLabel("Open form").setStyle(ButtonStyle.Primary),
      new ButtonBuilder().setCustomId("say_hi").setLabel("Say hi").setStyle(ButtonStyle.Success),
      new ButtonBuilder().setCustomId("preview_local").setLabel("Preview saved").setStyle(ButtonStyle.Secondary)
    );

    await message.channel.send({ embeds: [embed], components: [row] });
  }

  else if (cmd === "helpview") {
    const embed = new EmbedBuilder()
      .setTitle("Interactive Help")
      .setDescription("Click the buttons to get commands, environment variables, files, run instructions, or invite tips (ephemeral).")
      .setColor(0x1F8B4C);

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("help_commands").setLabel("Commands").setStyle(ButtonStyle.Primary),
      new ButtonBuilder().setCustomId("help_env").setLabel("Environment").setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId("help_files").setLabel("Files").setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId("help_run").setLabel("Run / Deploy").setStyle(ButtonStyle.Success)
    );

    await message.channel.send({ embeds: [embed], components: [row] });
  }
});

// Interaction handling: slash commands, buttons and modal submits
client.on("interactionCreate", async (interaction) => {
  try {
    // Handle slash commands
    if (interaction.isChatInputCommand()) {
      const { commandName } = interaction;

      if (commandName === "ping") {
        const sent = await interaction.reply({ content: "Pinging...", fetchReply: true });
        const latency = sent.createdTimestamp - interaction.createdTimestamp;
        await interaction.editReply(`Pong! Latency: ${latency}ms`);
      }

      else if (commandName === "echo") {
        const text = interaction.options.getString("text");
        await interaction.reply(text);
      }

      else if (commandName === "menu") {
        const embed = new EmbedBuilder()
          .setTitle("Test Menu")
          .setDescription("Press a button below to open the form, say hi, or preview local submissions.")
          .setColor(0x5865F2)
          .addFields({ name: "Note", value: "Submissions are saved to submissions.csv for local testing." });

        const row = new ActionRowBuilder().addComponents(
          new ButtonBuilder().setCustomId("open_form").setLabel("Open form").setStyle(ButtonStyle.Primary),
          new ButtonBuilder().setCustomId("say_hi").setLabel("Say hi").setStyle(ButtonStyle.Success),
          new ButtonBuilder().setCustomId("preview_local").setLabel("Preview saved").setStyle(ButtonStyle.Secondary)
        );

        await interaction.reply({ embeds: [embed], components: [row] });
      }

      else if (commandName === "helpview") {
        const embed = new EmbedBuilder()
          .setTitle("Interactive Help")
          .setDescription("Click the buttons to get commands, environment variables, files, run instructions, or invite tips (ephemeral).")
          .setColor(0x1F8B4C);

        const row = new ActionRowBuilder().addComponents(
          new ButtonBuilder().setCustomId("help_commands").setLabel("Commands").setStyle(ButtonStyle.Primary),
          new ButtonBuilder().setCustomId("help_env").setLabel("Environment").setStyle(ButtonStyle.Secondary),
          new ButtonBuilder().setCustomId("help_files").setLabel("Files").setStyle(ButtonStyle.Secondary),
          new ButtonBuilder().setCustomId("help_run").setLabel("Run / Deploy").setStyle(ButtonStyle.Success)
        );

        await interaction.reply({ embeds: [embed], components: [row] });
      }
    }

    else if (interaction.isButton()) {
      const id = interaction.customId;

      if (id === "open_form") {
        const modal = new ModalBuilder()
          .setCustomId("submit_modal")
          .setTitle("Submit a row (local test)");

        const nameInput = new TextInputBuilder()
          .setCustomId("name_input")
          .setLabel("Name")
          .setStyle(TextInputStyle.Short)
          .setPlaceholder("Your name")
          .setRequired(true)
          .setMaxLength(100);

        const messageInput = new TextInputBuilder()
          .setCustomId("message_input")
          .setLabel("Message")
          .setStyle(TextInputStyle.Paragraph)
          .setPlaceholder("Your message")
          .setRequired(true);

        modal.addComponents(
          new ActionRowBuilder().addComponents(nameInput),
          new ActionRowBuilder().addComponents(messageInput)
        );

        await interaction.showModal(modal);
      }

      else if (id === "say_hi") {
        await interaction.reply({ content: `Hello, ${interaction.user}!`, ephemeral: true });
      }

      else if (id === "preview_local") {
        if (!fs.existsSync(SUBMISSIONS_FILE)) {
          return interaction.reply({ content: "No local submissions yet.", ephemeral: true });
        }
        const content = fs.readFileSync(SUBMISSIONS_FILE, "utf8").trim().split("\n").slice(0, 10).map((line, i) => `${i + 1}. ${line}`).join("\n");
        if (content.length === 0) return interaction.reply({ content: "No local submissions yet.", ephemeral: true });
        const text = `Local submissions (up to 10):\n${content}`;
        if (text.length > 1900) {
          const buffer = Buffer.from(content, "utf8");
          const attachment = new AttachmentBuilder(buffer, { name: "preview.txt" });
          await interaction.reply({ content: "Preview attached.", files: [attachment], ephemeral: true });
        } else {
          await interaction.reply({ content: "```\n" + content + "\n```", ephemeral: true });
        }
      }

      // help buttons
      else if (id === "help_commands") {
        const e = new EmbedBuilder()
          .setTitle("Bot Commands")
          .addFields(
            { name: "!ping", value: "Replies with Pong and latency", inline: false },
            { name: "!echo <text>", value: "Echoes provided text", inline: false },
            { name: "!menu", value: "Sends an interactive menu (buttons + modal).", inline: false },
            { name: "!helpview", value: "Sends this interactive help view.", inline: false }
          ).setColor(0x5865F2);
        await interaction.reply({ embeds: [e], ephemeral: true });
      }

      else if (id === "help_env") {
        const e = new EmbedBuilder()
          .setTitle("Environment Variables")
          .addFields(
            { name: "BOT_TOKEN", value: "Discord bot token (required). Use host secrets (Replit/Render) or .env locally.", inline: false },
            { name: "BOT_PREFIX", value: "Command prefix (optional). Default: !", inline: false },
            { name: "GOOGLE_SERVICE_ACCOUNT_JSON_B64", value: "(Optional later) Base64 JSON for Google Sheets.", inline: false }
          ).setColor(0xFFD166);
        await interaction.reply({ embeds: [e], ephemeral: true });
      }

      else if (id === "help_files") {
        const e = new EmbedBuilder()
          .setTitle("Project Files")
          .addFields(
            { name: "index.js", value: "Main bot logic", inline: false },
            { name: "keep_alive.js", value: "Optional tiny webserver for Replit", inline: false },
            { name: "package.json", value: "Dependencies & start script", inline: false },
            { name: ".env.example", value: "Example env", inline: false }
          ).setColor(0x6AB04C);
        await interaction.reply({ embeds: [e], ephemeral: true });
      }

      else if (id === "help_run") {
        const e = new EmbedBuilder()
          .setTitle("Run & Deploy")
          .setDescription("Local: install deps then node index.js\nReplit: add files, set BOT_TOKEN as secret, Run\nRender: Background Worker start: node index.js")
          .setColor(0x2D9CDB);
        await interaction.reply({ embeds: [e], ephemeral: true });
      }
    }

    else if (interaction.isModalSubmit()) {
      if (interaction.customId === "submit_modal") {
        const name = interaction.fields.getTextInputValue("name_input");
        const messageText = interaction.fields.getTextInputValue("message_input");
        appendCsvRow([name, messageText, interaction.user.id, interaction.user.username]);
        await interaction.reply({ content: "Thanks — your input was received and saved locally.", ephemeral: true });
      }
    }
  } catch (err) {
    console.error("Interaction error:", err);
    try {
      if (!interaction.replied) await interaction.reply({ content: "An error occurred.", ephemeral: true });
    } catch (e) { /* ignore */ }
  }
});

client.once("ready", async () => {
  console.log(`Bot ready. Logged in as ${client.user.tag} (${client.user.id})`);

  // Register slash commands
  try {
    const commands = [
      {
        name: "ping",
        description: "Check bot latency"
      },
      {
        name: "echo",
        description: "Echoes your message",
        options: [
          {
            name: "text",
            type: 3, // STRING type
            description: "The text to echo",
            required: true
          }
        ]
      },
      {
        name: "menu",
        description: "Show the interactive menu with buttons"
      },
      {
        name: "helpview",
        description: "Show interactive help buttons"
      }
    ];

    await client.application.commands.set(commands);
    console.log(`Registered ${commands.length} slash commands globally.`);
  } catch (err) {
    console.error("Failed to register slash commands:", err);
  }
});

client.login(TOKEN);