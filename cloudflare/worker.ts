import { Container, getContainer } from "@cloudflare/containers";

export class FaceAttendContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "10m";
  enableInternet = true;
  pingEndpoint = "health";
  envVars = {
    PORT: "8080",
  };
}

interface Env {
  FACEATTEND_CONTAINER: any;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = getContainer(env.FACEATTEND_CONTAINER as any, "faceattend-api");
    return container.fetch(request);
  },
};
