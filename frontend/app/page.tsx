"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function Home() {
  const [status, setStatus] = useState("Ready");
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastAction, setLastAction] = useState<string | null>(
    null
  );

  const sessionIdRef = useRef<string>(
    crypto.randomUUID()
  );

  const mediaRecorderRef =
    useRef<MediaRecorder | null>(null);

  const streamRef =
    useRef<MediaStream | null>(null);

  const audioChunksRef =
    useRef<Blob[]>([]);

  const websocketRef =
    useRef<WebSocket | null>(null);

  const peerConnectionRef =
    useRef<RTCPeerConnection | null>(null);

  const realtimeDataChannelRef =
    useRef<RTCDataChannel | null>(null);

  const realtimeStreamRef =
    useRef<MediaStream | null>(null);

  const realtimeAudioRef =
    useRef<HTMLAudioElement | null>(null);

  const realtimeTranscriptItemsRef =
    useRef<Set<string>>(new Set());

  // --------------------------------------------------
  // REALTIME BOOKING CONFIRMATION STATE
  // --------------------------------------------------

  const realtimeBookingStateRef = useRef({
    customerName: null as string | null,
    nameConfirmed: false,
    appointmentConfirmed: false,
  });

  // --------------------------------------------------
  // FASTAPI WEBSOCKET
  // --------------------------------------------------

  useEffect(() => {
    const websocket = new WebSocket(
      "wss://api.tanimosoftware.com/ws/voice"
    );

    websocketRef.current = websocket;

    websocket.onopen = () => {
      console.log(
        "Voice WebSocket connected"
      );
    };

    websocket.onmessage = (event) => {
      console.log(
        "WebSocket message:",
        event.data
      );
    };

    websocket.onerror = () => {
      console.log(
        "WebSocket encountered an error"
      );
    };

    websocket.onclose = (event) => {
      console.log(
        "Voice WebSocket disconnected",
        {
          code: event.code,
          reason: event.reason,
          clean: event.wasClean,
        }
      );
    };

    return () => {
      websocket.close();
    };
  }, []);

  // ==================================================
  // OPENAI REALTIME VOICE
  // ==================================================

  const startRealtimeConversation = async () => {
    try {
      console.log(
        "Starting OpenAI Realtime..."
      );

      setStatus("Connecting Realtime...");
      setLastAction(null);

      // Reset transcript duplicate protection.
      realtimeTranscriptItemsRef.current.clear();

      // Reset booking confirmation state.
      realtimeBookingStateRef.current = {
        customerName: null,
        nameConfirmed: false,
        appointmentConfirmed: false,
      };

      // ----------------------------------------------
      // 1. GET EPHEMERAL REALTIME TOKEN
      // ----------------------------------------------

      const tokenResponse = await fetch(
       "https://api.tanimosoftware.com/api/realtime/token"
      );

      if (!tokenResponse.ok) {
        const errorText =
          await tokenResponse.text();

        console.error(
          "Realtime token error:",
          errorText
        );

        throw new Error(
          "Failed to get Realtime token"
        );
      }

      const tokenData =
        await tokenResponse.json();

      const ephemeralKey =
        tokenData.value;

      if (!ephemeralKey) {
        throw new Error(
          "Realtime token missing"
        );
      }

      // ----------------------------------------------
      // 2. CREATE WEBRTC CONNECTION
      // ----------------------------------------------

      const pc =
        new RTCPeerConnection();

      peerConnectionRef.current = pc;

      // ----------------------------------------------
      // 3. AI AUDIO OUTPUT
      // ----------------------------------------------

      const audio = new Audio();

      audio.autoplay = true;

      realtimeAudioRef.current =
        audio;

      pc.ontrack = (event) => {
        console.log(
          "Realtime AI audio received"
        );

        audio.srcObject =
          event.streams[0];
      };

      // ----------------------------------------------
      // 4. MICROPHONE
      // ----------------------------------------------

      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      realtimeStreamRef.current =
        stream;

      stream
        .getTracks()
        .forEach((track) => {
          pc.addTrack(
            track,
            stream
          );
        });

      // ----------------------------------------------
      // 5. OPENAI REALTIME DATA CHANNEL
      // ----------------------------------------------

      const dataChannel =
        pc.createDataChannel(
          "oai-events"
        );

      realtimeDataChannelRef.current =
        dataChannel;

      dataChannel.onopen = () => {
        console.log(
          "OpenAI Realtime data channel OPEN"
        );

        setStatus(
          "Realtime Voice Connected"
        );
      };

      // ==============================================
      // REALTIME EVENT HANDLER
      // ==============================================

      dataChannel.onmessage = async (event) => {
        const realtimeEvent =
          JSON.parse(event.data);

        console.log(
          "Realtime event:",
          realtimeEvent
        );

        // --------------------------------------------
        // USER TRANSCRIPT
        // --------------------------------------------

        if (
          realtimeEvent.type ===
          "conversation.item.input_audio_transcription.completed"
        ) {
          const transcript =
            realtimeEvent.transcript?.trim();

          const transcriptKey =
            `user:${realtimeEvent.item_id}`;

          if (
            transcript &&
            !realtimeTranscriptItemsRef.current.has(
              transcriptKey
            )
          ) {
            realtimeTranscriptItemsRef.current.add(
              transcriptKey
            );

            setMessages((previous) => [
              ...previous,
              {
                role: "user",
                text: transcript,
              },
            ]);
          }
        }

        // --------------------------------------------
        // ASSISTANT TRANSCRIPT
        // --------------------------------------------

        if (
          realtimeEvent.type ===
          "response.output_audio_transcript.done"
        ) {
          const transcript =
            realtimeEvent.transcript?.trim();

          const transcriptKey =
            `assistant:${realtimeEvent.item_id}`;

          if (
            transcript &&
            !realtimeTranscriptItemsRef.current.has(
              transcriptKey
            )
          ) {
            realtimeTranscriptItemsRef.current.add(
              transcriptKey
            );

            setMessages((previous) => [
              ...previous,
              {
                role: "assistant",
                text: transcript,
              },
            ]);
          }
        }

        // ============================================
        // REALTIME TOOL CALL
        // ============================================

        if (
          realtimeEvent.type ===
          "response.function_call_arguments.done"
        ) {
          console.log(
            "REALTIME TOOL CALL:",
            realtimeEvent.name,
            realtimeEvent.arguments
          );

          try {
            const toolArguments =
              JSON.parse(
                realtimeEvent.arguments ||
                  "{}"
              );

            let toolResult: any;

            // ========================================
            // TOOL 1:
            // CONFIRM CUSTOMER NAME
            // ========================================

            if (
              realtimeEvent.name ===
              "confirm_customer_name"
            ) {
              const confirmedName =
                String(
                  toolArguments.name || ""
                ).trim();

              if (!confirmedName) {
                toolResult = {
                  success: false,
                  error: "name_required",
                  message:
                    "A customer name is required.",
                };
              } else {
                realtimeBookingStateRef.current.customerName =
                  confirmedName;

                realtimeBookingStateRef.current.nameConfirmed =
                  true;

                toolResult = {
                  success: true,
                  name_confirmed: true,
                  name: confirmedName,
                  message:
                    "Customer name confirmation recorded.",
                };

                console.log(
                  "NAME CONFIRMED:",
                  confirmedName
                );

                setLastAction(
                  `✓ Name confirmed: ${confirmedName}`
                );
              }
            }

            // ========================================
            // TOOL 2:
            // CONFIRM APPOINTMENT
            // ========================================

            else if (
              realtimeEvent.name ===
              "confirm_appointment"
            ) {
              const appointmentDate =
                String(
                  toolArguments.appointment_date ||
                    ""
                ).trim();

              const appointmentTime =
                String(
                  toolArguments.appointment_time ||
                    ""
                ).trim();

              if (
                !appointmentDate ||
                !appointmentTime
              ) {
                toolResult = {
                  success: false,
                  error:
                    "appointment_details_required",
                  message:
                    "Appointment date and time are required.",
                };
              } else {
                realtimeBookingStateRef.current.appointmentConfirmed =
                  true;

                toolResult = {
                  success: true,
                  appointment_confirmed:
                    true,
                  appointment_date:
                    appointmentDate,
                  appointment_time:
                    appointmentTime,
                  message:
                    "Appointment confirmation recorded.",
                };

                console.log(
                  "APPOINTMENT CONFIRMED:",
                  appointmentDate,
                  appointmentTime
                );

                setLastAction(
                  "✓ Appointment details confirmed"
                );
              }
            }

            // ========================================
            // NORMAL BACKEND TOOLS
            // ========================================

            else {
              const toolResponse =
                await fetch(
                  "https://api.tanimosoftware.com/api/realtime/tool",
                  {
                    method: "POST",

                    headers: {
                      "Content-Type":
                        "application/json",
                    },

                    body: JSON.stringify({
                      name:
                        realtimeEvent.name,

                      arguments:
                        toolArguments,

                      name_confirmed:
                        realtimeBookingStateRef
                          .current
                          .nameConfirmed,

                      appointment_confirmed:
                        realtimeBookingStateRef
                          .current
                          .appointmentConfirmed,
                    }),
                  }
                );

              toolResult =
                await toolResponse.json();

              console.log(
                "REALTIME TOOL RESULT:",
                toolResult
              );

              // --------------------------------------
              // CREATE LEAD
              // --------------------------------------

              if (
                realtimeEvent.name ===
                "create_lead"
              ) {
                const businessResult =
                  toolResult?.result ??
                  toolResult;

                if (
                  toolResult?.success ===
                  false
                ) {
                  setLastAction(
                    "⚠ Lead not captured"
                  );
                } else if (
                  businessResult?.duplicate
                ) {
                  setLastAction(
                    "✓ Existing lead found"
                  );
                } else {
                  setLastAction(
                    "✓ Lead captured"
                  );
                }
              }

              // --------------------------------------
              // CREATE APPOINTMENT
              // --------------------------------------

              else if (
                realtimeEvent.name ===
                "create_appointment"
              ) {
                const businessResult =
                  toolResult?.result ??
                  toolResult;

                if (
                  toolResult?.success ===
                    false ||
                  businessResult?.success ===
                    false
                ) {
                  setLastAction(
                    "⚠ Appointment not scheduled"
                  );
                } else if (
                  businessResult?.duplicate
                ) {
                  setLastAction(
                    "✓ Existing appointment found"
                  );
                } else {
                  setLastAction(
                    "✓ Appointment scheduled"
                  );
                }
              }

              // --------------------------------------
              // CREATE LEAD AND APPOINTMENT
              // --------------------------------------

              else if (
                realtimeEvent.name ===
                "create_lead_and_appointment"
              ) {
                const businessResult =
                  toolResult?.result ??
                  toolResult;

                // ------------------------------------
                // HARD GUARD FAILURE
                // ------------------------------------

                if (
                  toolResult?.success ===
                    false ||
                  businessResult?.success ===
                    false
                ) {
                  const error =
                    businessResult?.error ||
                    toolResult?.error;

                  if (
                    error ===
                    "name_not_confirmed"
                  ) {
                    setLastAction(
                      "⚠ Customer name must be confirmed"
                    );
                  } else if (
                    error ===
                    "appointment_not_confirmed"
                  ) {
                    setLastAction(
                      "⚠ Appointment must be confirmed"
                    );
                  } else if (
                    error ===
                    "name_required"
                  ) {
                    setLastAction(
                      "⚠ Customer name required"
                    );
                  } else if (
                    error ===
                    "slot_unavailable"
                  ) {
                    setLastAction(
                      "⚠ Appointment slot unavailable"
                    );
                  } else {
                    setLastAction(
                      "⚠ Appointment not scheduled"
                    );
                  }
                }

                // ------------------------------------
                // BOOKING TOOL EXECUTED
                // ------------------------------------

                else {
                  const appointment =
                    businessResult
                      ?.appointment;

                  const appointmentSucceeded =
                    appointment?.success ===
                    true;

                  const leadDuplicate =
                    businessResult?.lead
                      ?.duplicate;

                  const appointmentDuplicate =
                    appointment?.duplicate;

                  if (
                    !appointmentSucceeded
                  ) {
                    setLastAction(
                      "✓ Lead captured • ⚠ Appointment not scheduled"
                    );
                  } else if (
                    leadDuplicate &&
                    appointmentDuplicate
                  ) {
                    setLastAction(
                      "✓ Existing customer • Existing appointment found"
                    );
                  } else if (
                    leadDuplicate
                  ) {
                    setLastAction(
                      "✓ Existing customer • New appointment scheduled"
                    );
                  } else if (
                    appointmentDuplicate
                  ) {
                    setLastAction(
                      "✓ Lead captured • Existing appointment found"
                    );
                  } else {
                    setLastAction(
                      "✓ Lead captured • Appointment scheduled"
                    );
                  }
                }
              }
            }

            // ========================================
            // RETURN TOOL RESULT TO OPENAI
            // ========================================

            dataChannel.send(
              JSON.stringify({
                type:
                  "conversation.item.create",

                item: {
                  type:
                    "function_call_output",

                  call_id:
                    realtimeEvent.call_id,

                  output:
                    JSON.stringify(
                      toolResult
                    ),
                },
              })
            );

            // ----------------------------------------
            // LET OPENAI CONTINUE SPEAKING
            // ----------------------------------------

            dataChannel.send(
              JSON.stringify({
                type:
                  "response.create",
              })
            );
          } catch (error) {
            console.error(
              "Realtime tool execution error:",
              error
            );

            setLastAction(
              "⚠ Tool execution error"
            );
          }
        }
      };

      // ==============================================
      // END OF DATA CHANNEL MESSAGE HANDLER
      // ==============================================

      dataChannel.onclose = () => {
        console.log(
          "OpenAI Realtime data channel CLOSED"
        );

        setStatus("Ready");
      };

      dataChannel.onerror = (event) => {
        console.error(
          "Realtime data channel error:",
          event
        );
      };

      // ----------------------------------------------
      // 6. CREATE SDP OFFER
      // ----------------------------------------------

      const offer =
        await pc.createOffer();

      await pc.setLocalDescription(
        offer
      );

      // ----------------------------------------------
      // 7. SEND SDP TO OPENAI
      // ----------------------------------------------

      const sdpResponse = await fetch(
        "https://api.openai.com/v1/realtime/calls",
        {
          method: "POST",

          body: offer.sdp,

          headers: {
            Authorization:
              `Bearer ${ephemeralKey}`,

            "Content-Type":
              "application/sdp",
          },
        }
      );

      if (!sdpResponse.ok) {
        const errorText =
          await sdpResponse.text();

        throw new Error(
          `Realtime connection failed: ${errorText}`
        );
      }

      // ----------------------------------------------
      // 8. RECEIVE SDP ANSWER
      // ----------------------------------------------

      const answerSdp =
        await sdpResponse.text();

      await pc.setRemoteDescription({
        type: "answer",
        sdp: answerSdp,
      });

      console.log(
        "OPENAI REALTIME CONNECTED"
      );

      setStatus(
        "Realtime Voice Connected"
      );
    } catch (error) {
      console.error(
        "Realtime error:",
        error
      );

      setStatus(
        "Realtime connection failed"
      );
    }
  };

  // ==================================================
  // STOP OPENAI REALTIME
  // ==================================================

  const stopRealtimeConversation = () => {
    console.log(
      "Stopping OpenAI Realtime..."
    );

    if (
      realtimeDataChannelRef.current
    ) {
      realtimeDataChannelRef.current.close();

      realtimeDataChannelRef.current =
        null;
    }

    if (
      peerConnectionRef.current
    ) {
      peerConnectionRef.current.close();

      peerConnectionRef.current =
        null;
    }

    if (
      realtimeStreamRef.current
    ) {
      realtimeStreamRef.current
        .getTracks()
        .forEach((track) => {
          track.stop();
        });

      realtimeStreamRef.current =
        null;
    }

    if (
      realtimeAudioRef.current
    ) {
      realtimeAudioRef.current.pause();

      realtimeAudioRef.current.srcObject =
        null;

      realtimeAudioRef.current =
        null;
    }

    // Reset confirmation state when conversation ends.
    realtimeBookingStateRef.current = {
      customerName: null,
      nameConfirmed: false,
      appointmentConfirmed: false,
    };

    setStatus("Ready");

    console.log(
      "OPENAI REALTIME STOPPED"
    );
  };

  // ==================================================
  // TURN-BASED VOICE
  // ==================================================

  async function startRecording() {
    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      streamRef.current =
        stream;

      audioChunksRef.current = [];

      const mediaRecorder =
        new MediaRecorder(stream);

      mediaRecorderRef.current =
        mediaRecorder;

      // ----------------------------------------------
      // AUDIO CHUNKS
      // ----------------------------------------------

      mediaRecorder.ondataavailable =
        async (event) => {
          console.log(
            "Audio chunk created:",
            event.data.size,
            "bytes"
          );

          if (
            event.data.size > 0
          ) {
            audioChunksRef.current.push(
              event.data
            );

            const websocket =
              websocketRef.current;

            console.log(
              "WebSocket state:",
              websocket?.readyState
            );

            if (
              websocket &&
              websocket.readyState ===
                WebSocket.OPEN
            ) {
              const audioBuffer =
                await event.data.arrayBuffer();

              websocket.send(
                audioBuffer
              );

              console.log(
                "Audio chunk sent:",
                audioBuffer.byteLength,
                "bytes"
              );
            }
          }
        };

      // ----------------------------------------------
      // USER PRESSES STOP
      // ----------------------------------------------

      mediaRecorder.onstop =
        async () => {
          try {
            setStatus(
              "Thinking..."
            );

            setLastAction(null);

            const audioBlob =
              new Blob(
                audioChunksRef.current,
                {
                  type:
                    mediaRecorder.mimeType ||
                    "audio/webm",
                }
              );

            const formData =
              new FormData();

            formData.append(
              "audio",
              audioBlob,
              "browser-recording.webm"
            );

            formData.append(
              "session_id",
              sessionIdRef.current
            );

            // ----------------------------------------
            // SEND AUDIO TO FASTAPI AGENT
            // ----------------------------------------

            const conversationResponse =
              await fetch(
                "https://api.tanimosoftware.com/api/voice/conversation",
                {
                  method: "POST",
                  body: formData,
                }
              );

            if (
              !conversationResponse.ok
            ) {
              const errorText =
                await conversationResponse.text();

              console.error(
                "Conversation API error:",
                errorText
              );

              throw new Error(
                `Conversation API returned ${conversationResponse.status}`
              );
            }

            const data =
              await conversationResponse.json();

            // ----------------------------------------
            // DISPLAY TRANSCRIPT
            // ----------------------------------------

            setMessages(
              (previous) => [
                ...previous,
                {
                  role: "user",
                  text:
                    data.transcript,
                },
                {
                  role: "assistant",
                  text:
                    data.response,
                },
              ]
            );

            // ----------------------------------------
            // DISPLAY BUSINESS ACTION
            // ----------------------------------------

            if (
              data.tool_called ===
              "create_lead"
            ) {
              if (
                data.tool_result
                  ?.duplicate
              ) {
                setLastAction(
                  "✓ Existing lead found"
                );
              } else {
                setLastAction(
                  "✓ Lead captured"
                );
              }
            }

            else if (
              data.tool_called ===
              "create_appointment"
            ) {
              if (
                data.tool_result
                  ?.success === false
              ) {
                setLastAction(
                  "⚠ Appointment not scheduled"
                );
              } else if (
                data.tool_result
                  ?.duplicate
              ) {
                setLastAction(
                  "✓ Existing appointment found"
                );
              } else {
                setLastAction(
                  "✓ Appointment scheduled"
                );
              }
            }

            else if (
              data.tool_called ===
              "create_lead_and_appointment"
            ) {
              const bookingSucceeded =
                data.tool_result
                  ?.success === true;

              const leadDuplicate =
                data.tool_result
                  ?.lead?.duplicate;

              const appointmentDuplicate =
                data.tool_result
                  ?.appointment
                  ?.duplicate;

              if (
                !bookingSucceeded
              ) {
                setLastAction(
                  "✓ Lead captured • ⚠ Appointment not scheduled"
                );
              } else if (
                leadDuplicate &&
                appointmentDuplicate
              ) {
                setLastAction(
                  "✓ Existing customer • Existing appointment found"
                );
              } else if (
                leadDuplicate
              ) {
                setLastAction(
                  "✓ Existing customer • New appointment scheduled"
                );
              } else if (
                appointmentDuplicate
              ) {
                setLastAction(
                  "✓ Lead captured • Existing appointment found"
                );
              } else {
                setLastAction(
                  "✓ Lead captured • Appointment scheduled"
                );
              }
            }

            // ----------------------------------------
            // TEXT TO SPEECH
            // ----------------------------------------

            setStatus(
              "AI is speaking..."
            );

            const ttsResponse =
              await fetch(
                "https://api.tanimosoftware.com/api/tts",
                {
                  method: "POST",

                  headers: {
                    "Content-Type":
                      "application/json",
                  },

                  body: JSON.stringify({
                    text:
                      data.response,
                  }),
                }
              );

            if (!ttsResponse.ok) {
              const errorText =
                await ttsResponse.text();

              console.error(
                "TTS API error:",
                errorText
              );

              throw new Error(
                `TTS API returned ${ttsResponse.status}`
              );
            }

            const responseAudioBlob =
              await ttsResponse.blob();

            const audioUrl =
              URL.createObjectURL(
                responseAudioBlob
              );

            const audio =
              new Audio(
                audioUrl
              );

            audio.onended = () => {
              setStatus("Ready");

              URL.revokeObjectURL(
                audioUrl
              );
            };

            await audio.play();
          } catch (error) {
            console.error(
              error
            );

            setStatus(
              "Something went wrong"
            );
          }
        };

      mediaRecorder.start(250);

      setIsRecording(true);

      setStatus(
        "Listening..."
      );
    } catch (error) {
      console.error(
        error
      );

      setStatus(
        "Microphone access denied"
      );
    }
  }

  // ==================================================
  // STOP TURN-BASED RECORDING
  // ==================================================

  function stopRecording() {
    const recorder =
      mediaRecorderRef.current;

    if (
      recorder &&
      recorder.state !==
        "inactive"
    ) {
      recorder.stop();
    }

    streamRef.current
      ?.getTracks()
      .forEach((track) => {
        track.stop();
      });

    setIsRecording(false);

    setStatus(
      "Processing..."
    );
  }
  // ==================================================
  // UI
  // ==================================================

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-white">
      <div className="mx-auto w-full max-w-2xl py-10">
        {/* HEADER */}
        <div className="mb-8 text-center">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            AI Agent Online
          </div>

          <h1 className="text-4xl font-bold">
            AI Voice Assistant
          </h1>

          <p className="mt-3 text-slate-400">
            Speak naturally. The AI can answer questions, capture
            leads, and schedule appointments.
          </p>
        </div>
        {/* PHONE DEMO */}
<div className="mb-8 rounded-2xl border border-sky-500/30 bg-sky-500/10 p-5 text-center">
  <p className="text-sm font-semibold uppercase tracking-wider text-sky-400">
    Live Phone Demo
  </p>

  <p className="mt-2 text-slate-300">
    Call the AI receptionist and speak with it live.
  </p>

  <a
    href="tel:+17432107468"
    className="mt-4 inline-block rounded-xl bg-sky-500 px-6 py-3 font-bold text-white shadow-lg transition hover:bg-sky-400"
  >
    ☎ Call AI Receptionist: (743) 210-7468
  </a>
</div>
        {/* VOICE CARD */}
        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
          <div className="flex flex-col items-center">
            {/* MICROPHONE */}
            <div
              className={`mb-6 flex h-28 w-28 items-center justify-center rounded-full ${
                isRecording
                  ? "animate-pulse bg-red-500/20"
                  : "bg-blue-500/10"
              }`}
            >
              <div
                className={`flex h-20 w-20 items-center justify-center rounded-full text-4xl shadow-lg ${
                  isRecording
                    ? "bg-red-600"
                    : "bg-blue-600"
                }`}
              >
                🎙️
              </div>
            </div>

            {/* STATUS */}
            <p className="text-sm uppercase tracking-widest text-slate-500">
              Status
            </p>

            <p className="mb-6 mt-2 text-xl font-semibold">
              {status}
            </p>

            {!isRecording ? (
              <>
                {/* TURN BASED */}
                <button
                  onClick={startRecording}
                  disabled={isRecording}
                  className={`
                    mx-auto w-full max-w-xl rounded-xl
                    border border-emerald-100
                    bg-gradient-to-b
                    from-emerald-200 via-emerald-300 to-emerald-500
                    px-5 py-3
                    text-base font-bold text-slate-900
                    shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(16,185,129,0.25)]
                    transition-all duration-150
                    hover:from-emerald-100
                    hover:via-emerald-200
                    hover:to-emerald-400
                    active:scale-[0.99]
                    disabled:opacity-50
                  `}
                >
                  Start Conversation
                </button>

                {/* REALTIME START */}
                <button
                  onClick={startRealtimeConversation}
                  className={`
                    mt-3 mx-auto w-full max-w-xl rounded-xl
                    border border-sky-100
                    bg-gradient-to-b
                    from-sky-200 via-sky-300 to-blue-500
                    px-5 py-3
                    text-base font-bold text-slate-900
                    shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(14,165,233,0.25)]
                    transition-all duration-150
                    hover:from-sky-100
                    hover:via-sky-200
                    hover:to-blue-400
                    active:scale-[0.99]
                  `}
                >
                  ▶ Start Realtime Voice
                </button>

                {/* REALTIME STOP */}
                <button
                  onClick={stopRealtimeConversation}
                  className={`
                    mt-3 mx-auto w-full max-w-xl rounded-xl
                    border border-rose-100
                    bg-gradient-to-b
                    from-rose-200 via-red-300 to-red-500
                    px-5 py-3
                    text-base font-bold text-slate-900
                    shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(239,68,68,0.25)]
                    transition-all duration-150
                    hover:from-rose-100
                    hover:via-red-200
                    hover:to-red-400
                    active:scale-[0.99]
                  `}
                >
                  ■ Stop Realtime Voice
                </button>
              </>
            ) : (
              <button
                onClick={stopRecording}
                className={`
                  w-full rounded-xl
                  border border-rose-100
                  bg-gradient-to-b
                  from-rose-200 via-red-300 to-red-500
                  px-6 py-4
                  font-bold text-slate-900
                  shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(239,68,68,0.25)]
                  transition-all duration-150
                  hover:from-rose-100
                  hover:via-red-200
                  hover:to-red-400
                  active:scale-[0.99]
                `}
              >
                Stop & Send
              </button>
            )}
          </div>
        </div>

        {/* CONVERSATION */}
        <div className="mt-6 rounded-3xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Conversation
            </h2>

            <span className="text-xs text-slate-500">
              Live transcript
            </span>
          </div>

          {messages.length === 0 ? (
            <p className="mt-6 text-center text-sm text-slate-500">
              Your conversation will appear here.
            </p>
          ) : (
            <div className="mt-6 space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={
                    message.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-800 text-slate-100"
                    }`}
                  >
                    <div className="mb-1 text-xs font-semibold opacity-70">
                      {message.role === "user"
                        ? "You"
                        : "AI Assistant"}
                    </div>

                    <p>{message.text}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* BUSINESS ACTION */}
          {lastAction && (
            <div className="mt-5 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
              {lastAction}
            </div>
          )}
        </div>

        {/* FEATURES */}
        <div className="mt-6 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl bg-slate-900 p-4">
            <div>🧠</div>
            <div className="mt-2 text-xs text-slate-400">
              AI Agent
            </div>
          </div>

          <div className="rounded-xl bg-slate-900 p-4">
            <div>👤</div>
            <div className="mt-2 text-xs text-slate-400">
              Lead Capture
            </div>
          </div>

          <div className="rounded-xl bg-slate-900 p-4">
            <div>📅</div>
            <div className="mt-2 text-xs text-slate-400">
              Scheduling
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
